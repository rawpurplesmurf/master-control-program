from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
import datetime
import logging

from mcp import schemas, models
from mcp.database import get_db
from mcp.cache import get_redis_client
from mcp.ollama import create_ollama_prompt, call_ollama
from mcp.action_executor import execute_actions
from mcp.prompt_history import prompt_history_manager
from mcp.ha_services import get_ha_services, refresh_ha_services_cache, get_ha_services_for_domain
from mcp.ha_action_executor import execute_ha_action, get_ha_action_history
from mcp.health_checks import (
    check_mysql_connection,
    check_redis_connection,
    check_home_assistant_connection,
    check_ollama_connection,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Helper function to format prompt template response
def _format_prompt_template_response(template):
    # Parse pre_fetch_data, handling both old dict format and new array format
    pre_fetch_data = []
    if template.pre_fetch_data:
        try:
            parsed_data = json.loads(template.pre_fetch_data)
            if isinstance(parsed_data, list):
                pre_fetch_data = parsed_data
            elif isinstance(parsed_data, dict):
                # Convert old dict format to array format for backward compatibility
                pre_fetch_data = list(parsed_data.keys()) if parsed_data else []
            else:
                pre_fetch_data = []
        except (json.JSONDecodeError, TypeError):
            pre_fetch_data = []
    
    return {
        "id": template.id,
        "template_name": template.template_name,
        "intent_keywords": template.intent_keywords,
        "system_prompt": template.system_prompt or "System prompt will be provided by active system prompt configuration.",
        "user_template": template.user_template,
        "pre_fetch_data": pre_fetch_data,
        "created_at": template.created_at.isoformat() if hasattr(template, 'created_at') and template.created_at else "",
        "updated_at": template.updated_at.isoformat() if hasattr(template, 'updated_at') and template.updated_at else ""
    }

# --- Prompt Templates CRUD Endpoints ---
@router.post("/api/prompts", response_model=schemas.PromptTemplateOut, status_code=201)
def create_prompt_template(template: schemas.PromptTemplateCreate, db: Session = Depends(get_db)):
    db_template = models.PromptTemplate(
        template_name=template.template_name,
        intent_keywords=template.intent_keywords,
        system_prompt=template.system_prompt,
        user_template=template.user_template,
        pre_fetch_data=json.dumps(template.pre_fetch_data),
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return _format_prompt_template_response(db_template)

@router.get("/api/prompts", response_model=List[schemas.PromptTemplateOut])
def list_prompt_templates(db: Session = Depends(get_db)):
    templates = db.query(models.PromptTemplate).all()
    return [_format_prompt_template_response(t) for t in templates]

@router.get("/api/prompts/{template_id}", response_model=schemas.PromptTemplateOut)
def get_prompt_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    return _format_prompt_template_response(template)

@router.put("/api/prompts/{template_id}", response_model=schemas.PromptTemplateOut)
def update_prompt_template(template_id: int, update: schemas.PromptTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    for field, value in update.dict(exclude_unset=True).items():
        if field == "pre_fetch_data":
            setattr(template, field, json.dumps(value))
        else:
            setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return _format_prompt_template_response(template)

@router.delete("/api/prompts/{template_id}", status_code=204)
def delete_prompt_template(template_id: int, db: Session = Depends(get_db)):
    template = db.query(models.PromptTemplate).filter(models.PromptTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Prompt template not found")
    db.delete(template)
    db.commit()
    return None

# --- System Prompt Management Endpoints ---
@router.get("/api/system-prompts", tags=["system-prompts"])
async def get_system_prompts(db: Session = Depends(get_db)):
    """Get all system prompts."""
    try:
        prompts = db.query(models.SystemPrompt).order_by(models.SystemPrompt.name).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "prompt": p.prompt,
                "description": p.description,
                "is_active": bool(p.is_active),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            }
            for p in prompts
        ]
    except Exception as e:
        logger.error(f"Error fetching system prompts: {e}")
        raise HTTPException(status_code=500, detail="Error fetching system prompts")

@router.get("/api/system-prompts/active", tags=["system-prompts"])
async def get_active_system_prompt(db: Session = Depends(get_db)):
    """Get the currently active system prompt."""
    try:
        active_prompt = db.query(models.SystemPrompt).filter(models.SystemPrompt.is_active == 1).first()
        
        if not active_prompt:
            # Return default fallback
            return {
                "name": "fallback",
                "prompt": "You are a helpful Home Assistant controller.",
                "description": "Fallback system prompt",
                "is_active": True
            }
        
        return {
            "id": active_prompt.id,
            "name": active_prompt.name,
            "prompt": active_prompt.prompt,
            "description": active_prompt.description,
            "is_active": bool(active_prompt.is_active)
        }
    except Exception as e:
        logger.error(f"Error fetching active system prompt: {e}")
        raise HTTPException(status_code=500, detail="Error fetching active system prompt")

@router.post("/api/system-prompts", tags=["system-prompts"])
async def create_system_prompt(
    prompt_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new system prompt."""
    try:
        # Validate required fields
        if not prompt_data.get('name') or not prompt_data.get('prompt'):
            raise HTTPException(status_code=400, detail="Name and prompt are required")
        
        # Check if name already exists
        existing = db.query(models.SystemPrompt).filter(models.SystemPrompt.name == prompt_data['name']).first()
        if existing:
            raise HTTPException(status_code=400, detail="System prompt name already exists")
        
        new_prompt = models.SystemPrompt(
            name=prompt_data['name'],
            prompt=prompt_data['prompt'],
            description=prompt_data.get('description', ''),
            is_active=1 if prompt_data.get('is_active', False) else 0
        )
        
        # If setting as active, deactivate others
        if new_prompt.is_active:
            db.query(models.SystemPrompt).update({models.SystemPrompt.is_active: 0})
        
        db.add(new_prompt)
        db.commit()
        db.refresh(new_prompt)
        
        logger.info(f"✅ Created system prompt: {new_prompt.name}")
        
        return {
            "id": new_prompt.id,
            "name": new_prompt.name,
            "prompt": new_prompt.prompt,
            "description": new_prompt.description,
            "is_active": bool(new_prompt.is_active),
            "message": "System prompt created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating system prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating system prompt")

@router.put("/api/system-prompts/{prompt_id}", tags=["system-prompts"])
async def update_system_prompt(
    prompt_id: int,
    prompt_data: dict,
    db: Session = Depends(get_db)
):
    """Update an existing system prompt."""
    try:
        prompt = db.query(models.SystemPrompt).filter(models.SystemPrompt.id == prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="System prompt not found")
        
        # Check if name conflicts with other prompts
        if 'name' in prompt_data and prompt_data['name'] != prompt.name:
            existing = db.query(models.SystemPrompt).filter(
                models.SystemPrompt.name == prompt_data['name'],
                models.SystemPrompt.id != prompt_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail="System prompt name already exists")
        
        # Update fields
        if 'name' in prompt_data:
            prompt.name = prompt_data['name']
        if 'prompt' in prompt_data:
            prompt.prompt = prompt_data['prompt']
        if 'description' in prompt_data:
            prompt.description = prompt_data['description']
        if 'is_active' in prompt_data:
            # If setting as active, deactivate others
            if prompt_data['is_active']:
                db.query(models.SystemPrompt).filter(models.SystemPrompt.id != prompt_id).update({models.SystemPrompt.is_active: 0})
            prompt.is_active = 1 if prompt_data['is_active'] else 0
        
        prompt.updated_at = datetime.datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Updated system prompt: {prompt.name}")
        
        return {
            "id": prompt.id,
            "name": prompt.name,
            "prompt": prompt.prompt,
            "description": prompt.description,
            "is_active": bool(prompt.is_active),
            "message": "System prompt updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating system prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error updating system prompt")

@router.post("/api/system-prompts/{prompt_id}/activate", tags=["system-prompts"])
async def activate_system_prompt(
    prompt_id: int,
    db: Session = Depends(get_db)
):
    """Activate a system prompt (deactivates all others)."""
    try:
        prompt = db.query(models.SystemPrompt).filter(models.SystemPrompt.id == prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="System prompt not found")
        
        # Deactivate all prompts
        db.query(models.SystemPrompt).update({models.SystemPrompt.is_active: 0})
        
        # Activate the selected prompt
        prompt.is_active = 1
        prompt.updated_at = datetime.datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Activated system prompt: {prompt.name}")
        
        return {
            "message": f"System prompt '{prompt.name}' is now active",
            "active_prompt": {
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating system prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error activating system prompt")

@router.delete("/api/system-prompts/{prompt_id}", tags=["system-prompts"])
async def delete_system_prompt(
    prompt_id: int,
    db: Session = Depends(get_db)
):
    """Delete a system prompt."""
    try:
        prompt = db.query(models.SystemPrompt).filter(models.SystemPrompt.id == prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="System prompt not found")
        
        prompt_name = prompt.name
        db.delete(prompt)
        db.commit()
        
        logger.info(f"✅ Deleted system prompt: {prompt_name}")
        
        return {"message": f"System prompt '{prompt_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting system prompt: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Error deleting system prompt")

import json
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from mcp import schemas, models
from mcp.database import get_db
from mcp.ollama import create_ollama_prompt, call_ollama

from mcp.action_executor import execute_actions
from mcp.ha_entity_log import get_entity_log, get_entity_log_summary, get_all_logged_entities
from mcp.health_checks import (
    check_mysql_connection,
    check_redis_connection,
    check_home_assistant_connection,
    check_ollama_connection,
    check_ha_websocket_connection,
)
import asyncio



# --- Healthcheck Endpoints ---
@router.get("/api/health/db", tags=["health"])
def health_db():
    try:
        check_mysql_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/api/health/redis", tags=["health"])
async def health_redis():
    try:
        await check_redis_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/api/health/ha", tags=["health"])
async def health_ha():
    try:
        await check_home_assistant_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/api/health/ollama", tags=["health"])
async def health_ollama():
    try:
        await check_ollama_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@router.get("/api/health/websocket", tags=["health"])
async def health_websocket():
    try:
        await check_ha_websocket_connection()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# --- Rules CRUD Endpoints ---
@router.get("/api/rules", response_model=List[schemas.RuleOut])
def list_rules(db: Session = Depends(get_db), rule_type: Optional[str] = None):
    """Get all rules, optionally filtered by type (skippy_guardrail or submind_automation)"""
    query = db.query(models.Rule)
    if rule_type:
        query = query.filter(models.Rule.rule_type == rule_type)
    rules = query.all()
    
    # Parse JSON fields and convert datetime fields for response
    for rule in rules:
        rule.blocked_actions = json.loads(rule.blocked_actions or '[]')
        rule.guard_conditions = json.loads(rule.guard_conditions or '{}')
        rule.trigger_conditions = json.loads(rule.trigger_conditions or '{}')
        rule.target_actions = json.loads(rule.target_actions or '[]')
        
        # Convert datetime fields to strings
        if rule.created_at:
            rule.created_at = rule.created_at.isoformat()
        if rule.updated_at:
            rule.updated_at = rule.updated_at.isoformat()
        if rule.last_executed:
            rule.last_executed = rule.last_executed.isoformat()
    
    return rules

@router.get("/api/rules/{rule_id}", response_model=schemas.RuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific rule by ID"""
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Parse JSON fields and convert datetime fields
    rule.blocked_actions = json.loads(rule.blocked_actions or '[]')
    rule.guard_conditions = json.loads(rule.guard_conditions or '{}')
    rule.trigger_conditions = json.loads(rule.trigger_conditions or '{}')
    rule.target_actions = json.loads(rule.target_actions or '[]')
    
    # Convert datetime fields to strings
    if rule.created_at:
        rule.created_at = rule.created_at.isoformat()
    if rule.updated_at:
        rule.updated_at = rule.updated_at.isoformat()
    if rule.last_executed:
        rule.last_executed = rule.last_executed.isoformat()
    
    return rule

@router.post("/api/rules", response_model=schemas.RuleOut)
def create_rule(rule: schemas.RuleCreate, db: Session = Depends(get_db)):
    """Create a new rule (skippy guardrail or submind automation)"""
    rule_data = rule.dict()
    
    # Convert JSON fields to strings - handle None values properly
    rule_data['blocked_actions'] = json.dumps(rule_data.get('blocked_actions') or [])
    rule_data['guard_conditions'] = json.dumps(rule_data.get('guard_conditions') or {})
    rule_data['trigger_conditions'] = json.dumps(rule_data.get('trigger_conditions') or {})
    rule_data['target_actions'] = json.dumps(rule_data.get('target_actions') or [])
    
    # Convert boolean to integer for compatibility
    if 'is_active' in rule_data:
        rule_data['is_active'] = int(rule_data['is_active'])
    
    db_rule = models.Rule(**rule_data)
    db.add(db_rule)
    try:
        db.commit()
        db.refresh(db_rule)
        
        # Parse JSON fields and convert datetime fields for response
        db_rule.blocked_actions = json.loads(db_rule.blocked_actions or '[]')
        db_rule.guard_conditions = json.loads(db_rule.guard_conditions or '{}')
        db_rule.trigger_conditions = json.loads(db_rule.trigger_conditions or '{}')
        db_rule.target_actions = json.loads(db_rule.target_actions or '[]')
        
        # Convert datetime fields to strings
        if db_rule.created_at:
            db_rule.created_at = db_rule.created_at.isoformat()
        if db_rule.updated_at:
            db_rule.updated_at = db_rule.updated_at.isoformat()
        if db_rule.last_executed:
            db_rule.last_executed = db_rule.last_executed.isoformat()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create rule: {e}")
    return db_rule

@router.put("/api/rules/{rule_id}", response_model=schemas.RuleOut)
def update_rule(rule_id: int = Path(...), rule: schemas.RuleUpdate = None, db: Session = Depends(get_db)):
    db_rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    update_data = rule.dict(exclude_unset=True)
    
    # Convert JSON fields to strings
    if 'blocked_actions' in update_data:
        update_data['blocked_actions'] = json.dumps(update_data['blocked_actions'])
    if 'guard_conditions' in update_data:
        update_data['guard_conditions'] = json.dumps(update_data['guard_conditions'])
    if 'trigger_conditions' in update_data:
        update_data['trigger_conditions'] = json.dumps(update_data['trigger_conditions'])
    if 'target_actions' in update_data:
        update_data['target_actions'] = json.dumps(update_data['target_actions'])
    
    # Convert boolean to integer for compatibility
    if 'is_active' in update_data:
        update_data['is_active'] = int(update_data['is_active'])
    
    for field, value in update_data.items():
        setattr(db_rule, field, value)
    
    db_rule.updated_at = datetime.datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(db_rule)
        
        # Parse JSON fields and convert datetime fields for response
        db_rule.blocked_actions = json.loads(db_rule.blocked_actions or '[]')
        db_rule.guard_conditions = json.loads(db_rule.guard_conditions or '{}')
        db_rule.trigger_conditions = json.loads(db_rule.trigger_conditions or '{}')
        db_rule.target_actions = json.loads(db_rule.target_actions or '[]')
        
        # Convert datetime fields to strings
        if db_rule.created_at:
            db_rule.created_at = db_rule.created_at.isoformat()
        if db_rule.updated_at:
            db_rule.updated_at = db_rule.updated_at.isoformat()
        if db_rule.last_executed:
            db_rule.last_executed = db_rule.last_executed.isoformat()
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not update rule: {e}")
    return db_rule

@router.delete("/api/rules/{rule_id}", response_model=dict)
def delete_rule(rule_id: int = Path(...), db: Session = Depends(get_db)):
    db_rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(db_rule)
    db.commit()
    return {"detail": "Rule deleted"}

@router.post("/api/rules/{rule_id}/execute")
def execute_rule(rule_id: int, db: Session = Depends(get_db)):
    """Manually execute a submind automation rule"""
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if rule.rule_type != 'submind_automation':
        raise HTTPException(status_code=400, detail="Only submind automation rules can be executed manually")
    
    if not rule.is_active:
        raise HTTPException(status_code=400, detail="Rule is not active")
    
    # Parse target actions and execute them
    try:
        target_actions = json.loads(rule.target_actions or '[]')
        for action in target_actions:
            # Execute the action (implementation would depend on action executor)
            # For now, just log the execution
            print(f"Executing action for rule {rule.rule_name}: {action}")
        
        # Update execution metadata
        rule.last_executed = datetime.datetime.utcnow()
        rule.execution_count += 1
        db.commit()
        
        return {"message": f"Rule '{rule.rule_name}' executed successfully", "actions_executed": len(target_actions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute rule: {str(e)}")

# --- Data Fetcher Management Endpoints ---
@router.get("/api/data-fetchers", response_model=list, tags=["data-fetchers"])
def list_data_fetchers(db: Session = Depends(get_db)):
    """List all data fetchers"""
    fetchers = db.query(models.DataFetcher).all()
    return [
        {
            "id": f.id,
            "fetcher_key": f.fetcher_key,
            "description": f.description,
            "ttl_seconds": f.ttl_seconds,
            "is_active": bool(f.is_active),
            "created_at": f.created_at.isoformat() if f.created_at else "",
            "updated_at": f.updated_at.isoformat() if f.updated_at else ""
        }
        for f in fetchers
    ]

@router.post("/api/data-fetchers", response_model=schemas.DataFetcherOut, status_code=201, tags=["data-fetchers"])
def create_data_fetcher(fetcher: schemas.DataFetcherCreate, db: Session = Depends(get_db)):
    """Create a new data fetcher"""
    # Check if fetcher_key already exists
    existing = db.query(models.DataFetcher).filter(models.DataFetcher.fetcher_key == fetcher.fetcher_key).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Data fetcher with key '{fetcher.fetcher_key}' already exists")
    
    fetcher_data = fetcher.dict()
    if 'is_active' in fetcher_data:
        fetcher_data['is_active'] = 1 if fetcher_data['is_active'] else 0
    db_fetcher = models.DataFetcher(**fetcher_data)
    db.add(db_fetcher)
    try:
        db.commit()
        db.refresh(db_fetcher)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not create data fetcher: {e}")
    
    return _format_data_fetcher_response(db_fetcher)

@router.get("/api/data-fetchers/{fetcher_key}", response_model=schemas.DataFetcherOut, tags=["data-fetchers"])
def get_data_fetcher(fetcher_key: str, db: Session = Depends(get_db)):
    """Get a specific data fetcher"""
    fetcher = db.query(models.DataFetcher).filter(models.DataFetcher.fetcher_key == fetcher_key).first()
    if not fetcher:
        raise HTTPException(status_code=404, detail="Data fetcher not found")
    return _format_data_fetcher_response(fetcher)

@router.put("/api/data-fetchers/{fetcher_key}", response_model=schemas.DataFetcherOut, tags=["data-fetchers"])
def update_data_fetcher(fetcher_key: str, fetcher_update: schemas.DataFetcherUpdate, db: Session = Depends(get_db)):
    """Update a data fetcher"""
    db_fetcher = db.query(models.DataFetcher).filter(models.DataFetcher.fetcher_key == fetcher_key).first()
    if not db_fetcher:
        raise HTTPException(status_code=404, detail="Data fetcher not found")
    
    # Update only provided fields
    update_data = fetcher_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'is_active':
            value = 1 if value else 0
        setattr(db_fetcher, field, value)
    
    try:
        db.commit()
        db.refresh(db_fetcher)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Could not update data fetcher: {e}")
    
    return _format_data_fetcher_response(db_fetcher)

@router.delete("/api/data-fetchers/{fetcher_key}", status_code=204, tags=["data-fetchers"])
def delete_data_fetcher(fetcher_key: str, db: Session = Depends(get_db)):
    """Delete a data fetcher"""
    fetcher = db.query(models.DataFetcher).filter(models.DataFetcher.fetcher_key == fetcher_key).first()
    if not fetcher:
        raise HTTPException(status_code=404, detail="Data fetcher not found")
    db.delete(fetcher)
    db.commit()
    return None

@router.post("/api/data-fetchers/{fetcher_key}/refresh", tags=["data-fetchers"])
def refresh_data_fetcher(fetcher_key: str):
    """Force refresh a specific data fetcher (bypass cache)"""
    from mcp.data_fetcher_engine import get_prefetch_data
    result = get_prefetch_data(fetcher_key, force_refresh=True)
    return {"fetcher_key": fetcher_key, "result": result, "refreshed_at": datetime.datetime.now().isoformat()}

@router.get("/api/data-fetchers/{fetcher_key}/test", tags=["data-fetchers"])
def test_data_fetcher(fetcher_key: str):
    """Test a data fetcher (always fresh, no caching)"""
    from mcp.data_fetcher_engine import get_prefetch_data
    result = get_prefetch_data(fetcher_key, force_refresh=True)
    return {"fetcher_key": fetcher_key, "result": result, "tested_at": datetime.datetime.now().isoformat()}

def _format_data_fetcher_response(fetcher) -> dict:
    """Helper function to format data fetcher response"""
    return {
        "id": fetcher.id,
        "fetcher_key": fetcher.fetcher_key,
        "description": fetcher.description,
        "ttl_seconds": fetcher.ttl_seconds,
        "python_code": fetcher.python_code,
        "is_active": bool(fetcher.is_active),
        "created_at": fetcher.created_at.isoformat() if fetcher.created_at else "",
        "updated_at": fetcher.updated_at.isoformat() if fetcher.updated_at else ""
    }

# Alias for /api/health/homeassistant
@router.get("/api/health/homeassistant", tags=["health"])
async def health_homeassistant():
    return await health_ha()

# --- Home Assistant Entities Endpoint ---
@router.get("/api/ha/entities", tags=["home-assistant"])
async def get_ha_entities():
    """Get all Home Assistant entities from Redis cache"""
    try:
        import redis
        import json
        import os
        import requests
        
        # Get Redis connection
        REDIS_URL = os.environ.get("REDIS_URL")
        if not REDIS_URL:
            host = os.environ.get("REDIS_HOST", "localhost")
            port = os.environ.get("REDIS_PORT", "6379")
            REDIS_URL = f"redis://{host}:{port}/0"
        
        r = redis.Redis.from_url(REDIS_URL)
        
        # Get cached entities
        cached_entities = r.get("ha:entities")
        if not cached_entities:
            # If no cache, try to fetch directly from HA
            HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
            HA_TOKEN = os.environ.get("HA_TOKEN", "your_long_lived_access_token")
            
            headers = {
                "Authorization": f"Bearer {HA_TOKEN}",
                "Content-Type": "application/json",
            }
            
            resp = requests.get(f"{HA_URL}/api/states", headers=headers, timeout=10)
            resp.raise_for_status()
            all_entities = resp.json()
            
            # Cache the result for future requests
            r.set("ha:entities", json.dumps(all_entities), ex=60)  # Cache for 1 minute
            return all_entities
        
        entities = json.loads(cached_entities)
        return entities
        
    except redis.RedisError as e:
        raise HTTPException(status_code=503, detail=f"Redis connection error: {str(e)}")
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Home Assistant connection error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching HA entities: {str(e)}")

@router.post("/api/command")
async def process_command(command_input: schemas.CommandInput, db: Session = Depends(get_db)):
    """
    Process a natural language command through the complete MCP pipeline.
    
    This endpoint:
    1. Determines which prompt template to use (hardcoded to 'default' for now)
    2. Executes all required data fetchers for the template
    3. Constructs the prompt with fetched data
    4. Sends the prompt to the LLM
    5. Returns the LLM response with metadata
    
    Future enhancements will include:
    - Intent matching to automatically select the best template
    - Guardrail evaluation to prevent inappropriate actions
    - Action execution for commands that require HA interaction
    """
    logger.info(f"Received command: {command_input.command}")
    
    try:
        from mcp.command_processor import process_command_pipeline
        
        # Process through the complete pipeline
        result = await process_command_pipeline(command_input.command, db, source=command_input.source)
        
        # Log command history for auditing
        try:
            history_entry = models.PromptHistory(
                user_command=command_input.command,
                ollama_response=result.get("response", ""),
                executed_actions="[]",  # Will be updated when action execution is implemented
                status="success" if result.get("success", False) else "failed"
            )
            db.add(history_entry)
            db.commit()
        except Exception as history_error:
            logger.error(f"Failed to log command history: {history_error}")
            # Don't fail the request if history logging fails
        
        logger.info(f"Command processing result: {result.get('success', False)}")
        return result
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in process_command for '{command_input.command}': {traceback.format_exc()}")
        
        logger.error(f"Unexpected error in command endpoint: {str(e)}", exc_info=True)
        
        # Log failure
        try:
            history_entry = models.PromptHistory(
                user_command=command_input.command, 
                ollama_response=f"Error: {str(e)}", 
                executed_actions="[]", 
                status="failed"
            )
            db.add(history_entry)
            db.commit()
        except Exception as history_error:
            logger.error(f"Failed to log error history: {history_error}")
        
        return {
            "response": f"I'm sorry, I encountered an unexpected error: {str(e)}",
            "error": "command_endpoint_error",
            "success": False
        }

# Prompt History Endpoints
@router.get("/api/prompt-history", response_model=List[schemas.PromptHistoryOut])
async def get_prompt_history(
    limit: int = 100,
    offset: int = 0,
    source: Optional[str] = None
):
    """
    Get prompt history with optional filtering and pagination.
    
    Query Parameters:
    - limit: Maximum number of interactions to return (default: 100)
    - offset: Number of interactions to skip for pagination (default: 0)
    - source: Filter by source (api, skippy, submind, rerun, manual)
    """
    try:
        interactions = await prompt_history_manager.get_prompt_history(
            limit=limit,
            offset=offset,
            source_filter=source
        )
        return interactions
    except Exception as e:
        logger.error(f"Error retrieving prompt history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving prompt history: {str(e)}")

@router.get("/api/prompt-history/stats", response_model=schemas.PromptHistoryStats)
async def get_prompt_history_stats():
    """
    Get statistics about prompt history including total count and source distribution.
    """
    try:
        stats = await prompt_history_manager.get_history_stats()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving prompt history stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving prompt history stats: {str(e)}")

@router.get("/api/prompt-history/{interaction_id}", response_model=schemas.PromptHistoryOut)
async def get_prompt_interaction(interaction_id: str):
    """
    Get a specific prompt interaction by ID.
    """
    try:
        interaction = await prompt_history_manager.get_prompt_interaction(interaction_id)
        if not interaction:
            raise HTTPException(status_code=404, detail=f"Prompt interaction {interaction_id} not found")
        return interaction
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving prompt interaction {interaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving prompt interaction: {str(e)}")

@router.post("/api/prompt-history/{interaction_id}/rerun", response_model=schemas.PromptRerunResponse)
async def rerun_prompt_interaction(interaction_id: str):
    """
    Re-run a previous prompt interaction with the same prompt.
    
    This will:
    1. Retrieve the original prompt
    2. Send it to the LLM again
    3. Store the new interaction
    4. Return the new response
    """
    try:
        result = await prompt_history_manager.rerun_prompt_interaction(interaction_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-running prompt interaction {interaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error re-running prompt interaction: {str(e)}")

@router.delete("/api/prompt-history/{interaction_id}")
async def delete_prompt_interaction(interaction_id: str):
    """
    Delete a specific prompt interaction from history.
    """
    try:
        deleted = await prompt_history_manager.delete_prompt_interaction(interaction_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Prompt interaction {interaction_id} not found")
        
        return {"message": f"Prompt interaction {interaction_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt interaction {interaction_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting prompt interaction: {str(e)}")

# --- Home Assistant Entity Log Endpoints ---
@router.get("/api/ha/entities/log/{entity_id}", tags=["ha-logs"])
async def get_ha_entity_log(
    entity_id: str, 
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of log entries to return"),
    start_date: Optional[str] = Query(None, description="Start date in ISO format (e.g., 2025-10-01T00:00:00Z)"),
    end_date: Optional[str] = Query(None, description="End date in ISO format (e.g., 2025-10-03T23:59:59Z)")
):
    """
    Get state change log for a specific Home Assistant entity.
    
    Returns chronological log of all state changes for the specified entity
    with optional date range filtering.
    """
    try:
        log_entries = await get_entity_log(entity_id, limit, start_date, end_date)
        
        return {
            "entity_id": entity_id,
            "log_entries": log_entries,
            "count": len(log_entries),
            "limit": limit,
            "start_date": start_date,
            "end_date": end_date
        }
        
    except Exception as e:
        logger.error(f"Error retrieving entity log for {entity_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving entity log: {str(e)}"
        )

@router.get("/api/ha/entities/log/{entity_id}/summary", tags=["ha-logs"])
async def get_ha_entity_log_summary_endpoint(
    entity_id: str,
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze")
):
    """
    Get summary statistics for an entity's state changes over the specified period.
    
    Returns statistics like total changes, state vs attribute changes, and frequency.
    """
    try:
        summary = await get_entity_log_summary(entity_id, days)
        return summary
        
    except Exception as e:
        logger.error(f"Error getting entity log summary for {entity_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting entity log summary: {str(e)}"
        )

@router.get("/api/ha/entities/logs", tags=["ha-logs"])
async def get_all_ha_entity_logs(domain: Optional[str] = Query(None, description="Filter by domain (e.g., 'light', 'switch')")):
    """
    Get list of all entities that have state change logs.
    
    Returns a list of entity IDs that have logged state changes.
    Optionally filter by domain.
    """
    try:
        entity_ids = await get_all_logged_entities()
        
        # Filter by domain if specified
        if domain:
            entity_ids = [eid for eid in entity_ids if eid.startswith(f"{domain}.")]
        
        return {
            "logged_entities": entity_ids,
            "count": len(entity_ids),
            "domain_filter": domain
        }
        
    except Exception as e:
        logger.error(f"Error getting logged entities: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting logged entities: {str(e)}"
        )

# --- WebSocket Diagnostics Endpoints ---
@router.get("/api/ha/websocket/status", tags=["diagnostics"])
async def get_websocket_status():
    """
    Get Home Assistant WebSocket connection status and diagnostics.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        client = get_ha_websocket_client()
        
        if not client:
            return {
                "connected": False,
                "authenticated": False,
                "running": False,
                "error": "WebSocket client not initialized"
            }
        
        # Check if websocket is connected (handle different websocket library versions)
        websocket_connected = False
        if client.websocket is not None:
            try:
                websocket_connected = not getattr(client.websocket, 'closed', False)
            except:
                websocket_connected = client.websocket is not None
        
        return {
            "connected": websocket_connected,
            "authenticated": client.is_authenticated,
            "running": client.is_running,
            "redis_connected": client.redis_client is not None,
            "message_id": client.message_id,
            "reconnect_delay": client.reconnect_delay
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting WebSocket status: {str(e)}"
        )

@router.get("/api/ha/entities/log/debug/{entity_id}", tags=["diagnostics"])
async def debug_entity_log(entity_id: str):
    """
    Debug endpoint to check entity log storage in Redis.
    """
    try:
        redis_client = get_redis_client()
        log_key = f"ha:log:{entity_id}"
        
        # Check if the key exists
        exists = await redis_client.exists(log_key)
        
        # Get the count of entries
        count = await redis_client.zcard(log_key) if exists else 0
        
        # Get TTL
        ttl = await redis_client.ttl(log_key) if exists else -1
        
        # Get all entries (for debugging)
        entries = []
        if exists and count > 0:
            raw_entries = await redis_client.zrevrange(log_key, 0, -1)
            for entry in raw_entries:
                try:
                    if isinstance(entry, bytes):
                        entries.append(json.loads(entry.decode()))
                    else:
                        entries.append(json.loads(entry))
                except json.JSONDecodeError:
                    entries.append({"error": "Invalid JSON", "raw": entry.decode() if isinstance(entry, bytes) else str(entry)})
        
        return {
            "entity_id": entity_id,
            "log_key": log_key,
            "key_exists": bool(exists),
            "entry_count": count,
            "ttl_seconds": ttl,
            "entries": entries
        }
        
    except Exception as e:
        logger.error(f"Error debugging entity log for {entity_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error debugging entity log: {str(e)}"
        )

@router.get("/api/ha/redis/keys", tags=["diagnostics"])
async def get_redis_keys(pattern: str = Query("ha:log:*", description="Redis key pattern to search for")):
    """
    Get Redis keys matching a pattern for debugging.
    """
    try:
        redis_client = get_redis_client()
        keys = await redis_client.keys(pattern)
        
        # Convert bytes keys to strings
        string_keys = []
        for key in keys:
            if isinstance(key, bytes):
                string_keys.append(key.decode('utf-8'))
            else:
                string_keys.append(str(key))
        
        return {
            "pattern": pattern,
            "keys": sorted(string_keys),
            "count": len(string_keys)
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis keys: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting Redis keys: {str(e)}"
        )

@router.post("/api/ha/test/log/{entity_id}", tags=["diagnostics"])
async def test_manual_log(entity_id: str):
    """
    Manually test logging for an entity by creating a fake state change.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        client = get_ha_websocket_client()
        if not client:
            raise HTTPException(status_code=500, detail="WebSocket client not available")
        
        # Create fake state change data
        old_state = {"state": "off", "attributes": {"friendly_name": "Test Entity"}}
        new_state = {"state": "on", "attributes": {"friendly_name": "Test Entity"}}
        
        # Call the logging method directly
        await client._log_state_change(entity_id, old_state, new_state)
        
        return {
            "success": True,
            "message": f"Manually logged state change for {entity_id}",
            "old_state": old_state,
            "new_state": new_state
        }
        
    except Exception as e:
        logger.error(f"Error testing manual log: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing manual log: {str(e)}"
        )

@router.post("/api/ha/test/resubscribe", tags=["diagnostics"])
async def test_resubscribe():
    """
    Test resubscribing to WebSocket events.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        client = get_ha_websocket_client()
        if not client:
            raise HTTPException(status_code=500, detail="WebSocket client not available")
        
        if not client.is_authenticated:
            return {"success": False, "message": "WebSocket not authenticated"}
        
        # Try to resubscribe to events
        success = await client.subscribe_to_events()
        
        return {
            "success": success,
            "message": "Resubscribed to events" if success else "Failed to resubscribe",
            "websocket_status": {
                "connected": client.websocket is not None,
                "authenticated": client.is_authenticated,
                "message_id": client.message_id
            }
        }
        
    except Exception as e:
        logger.error(f"Error testing resubscribe: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing resubscribe: {str(e)}"
        )

@router.post("/api/ha/test/restart-websocket", tags=["diagnostics"])
async def restart_websocket():
    """
    Restart the WebSocket connection to Home Assistant.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        client = get_ha_websocket_client()
        if not client:
            raise HTTPException(status_code=500, detail="WebSocket client not available")
        
        # Stop and restart the client
        await client.stop()
        
        # Start in background
        import asyncio
        asyncio.create_task(client.start())
        
        # Give it a moment to connect
        await asyncio.sleep(2)
        
        return {
            "success": True,
            "message": "WebSocket client restarted",
            "status": {
                "connected": client.websocket is not None,
                "authenticated": client.is_authenticated,
                "running": client.is_running
            }
        }
        
    except Exception as e:
        logger.error(f"Error restarting WebSocket: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error restarting WebSocket: {str(e)}"
        )

@router.get("/api/ha/websocket/messages", tags=["diagnostics"])
async def get_recent_websocket_messages():
    """
    Get recent WebSocket messages for debugging.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        client = get_ha_websocket_client()
        if not client:
            raise HTTPException(status_code=500, detail="WebSocket client not available")
        
        messages = getattr(client, 'recent_messages', [])
        
        return {
            "message_count": len(messages),
            "recent_messages": messages,
            "websocket_status": {
                "connected": client.websocket is not None,
                "authenticated": client.is_authenticated,
                "running": client.is_running
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting WebSocket messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting WebSocket messages: {str(e)}"
        )

# --- Home Assistant Services and Actions ---

@router.get("/api/ha/services", tags=["home_assistant"])
async def get_available_services(
    refresh: bool = Query(False, description="Force refresh from Home Assistant"),
    domain: str = Query(None, description="Filter by specific domain")
):
    """
    Get available Home Assistant services with real-time data.
    
    Fetches live service information from Home Assistant's /api/services endpoint
    with Redis caching for performance.
    """
    try:
        if refresh:
            logger.info("🔄 Force refreshing HA services cache")
            services_data = await refresh_ha_services_cache()
        else:
            services_data = await get_ha_services(use_cache=True)
        
        # Filter by domain if requested
        if domain:
            domain_services = services_data.get("services", {}).get(domain, [])
            return {
                "domain": domain,
                "services": {domain: domain_services},
                "total_services": len(domain_services),
                "total_domains": 1 if domain_services else 0,
                "last_updated": services_data.get("last_updated"),
                "cached": not refresh and not services_data.get("fallback", False)
            }
        
        return {
            **services_data,
            "cached": not refresh and not services_data.get("fallback", False)
        }
        
    except Exception as e:
        logger.error(f"Error getting HA services: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving services: {str(e)}"
        )

@router.post("/api/ha/action", tags=["home_assistant"])
async def execute_home_assistant_action(
    action: dict,
    background_tasks: BackgroundTasks
):
    """
    Execute an action on a Home Assistant device.
    
    Validates service exists in HA, checks entity controllability,
    and logs all actions with 7-day retention.
    """
    try:
        result = await execute_ha_action(action)
        
        if result['success']:
            logger.info(f"✅ Action executed successfully: {action.get('service')} on {action.get('entity_id')}")
        else:
            logger.warning(f"❌ Action failed: {result.get('error')}")
        
        return result
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in execute_home_assistant_action for {action}: {traceback.format_exc()}")
        
        logger.error(f"Error executing HA action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing action: {str(e)}"
        )

@router.post("/api/ha/actions/bulk", tags=["home_assistant"])
async def execute_bulk_actions(
    actions: List[dict],
    background_tasks: BackgroundTasks
):
    """
    Execute multiple Home Assistant actions in sequence.
    
    Returns results for each action with overall success status.
    Useful for scenes, automation sequences, and batch operations.
    """
    if len(actions) > 50:  # Reasonable limit
        raise HTTPException(
            status_code=400,
            detail="Too many actions. Maximum 50 actions per bulk request."
        )
    
    try:
        
        results = []
        overall_success = True
        
        for i, action in enumerate(actions):
            logger.info(f"🔄 Executing bulk action {i+1}/{len(actions)}: {action}")
            
            result = await execute_ha_action(action)
            results.append({
                "action_index": i,
                "action": action,
                "result": result
            })
            
            if not result.get('success'):
                overall_success = False
        
        return {
            "success": overall_success,
            "total_actions": len(actions),
            "successful_actions": sum(1 for r in results if r['result'].get('success')),
            "failed_actions": sum(1 for r in results if not r['result'].get('success')),
            "results": results,
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in execute_bulk_actions for {actions}: {traceback.format_exc()}")
        
        logger.error(f"Error executing bulk actions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error executing bulk actions: {str(e)}"
        )

@router.get("/api/ha/entities/{entity_id}/actions", tags=["home_assistant"])
async def get_entity_action_history(
    entity_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of actions to return")
):
    """
    Get action execution history for a specific entity.
    
    Returns chronological list of all actions executed on the entity
    with 7-day retention from Redis logs.
    """
    try:
        history = await get_ha_action_history(entity_id, limit)
        
        return {
            "entity_id": entity_id,
            "actions": history,
            "count": len(history),
            "limit": limit,
            "has_more": len(history) == limit  # Hint if there might be more
        }
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in get_entity_action_history for {entity_id}: {traceback.format_exc()}")
        
        logger.error(f"Error getting action history for {entity_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting action history: {str(e)}"
        )

@router.post("/api/ha/cache/cleanup", tags=["home_assistant"])
async def cleanup_ha_cache():
    """
    Manually trigger cleanup of stale Home Assistant entities from Redis cache.
    
    Compares cached entities with current Home Assistant state and removes
    any entities that no longer exist in HA. This is normally done automatically
    every hour by the WebSocket client, but can be triggered manually here.
    """
    try:
        from mcp.ha_websocket import get_ha_websocket_client
        
        # Get the WebSocket client instance
        websocket_client = get_ha_websocket_client()
        
        if not websocket_client:
            raise HTTPException(
                status_code=503,
                detail="Home Assistant WebSocket client not available"
            )
        
        # Trigger the cleanup
        await websocket_client._cleanup_stale_cache_entries()
        
        return {
            "success": True,
            "message": "Cache cleanup completed successfully",
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in cleanup_ha_cache: {traceback.format_exc()}")
        
        logger.error(f"Error during cache cleanup: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error during cache cleanup: {str(e)}"
        )

@router.get("/api/ha/cache/info", tags=["home_assistant"])
async def get_ha_cache_info():
    """
    Get information about the current Home Assistant cache state.
    
    Returns statistics about cached entities, domains, and cache metadata.
    Useful for monitoring and debugging cache consistency.
    """
    try:
        redis_client = get_redis_client()
        if not redis_client:
            raise HTTPException(
                status_code=503,
                detail="Redis client not available"
            )
        
        # Get cache metadata
        metadata_data = await redis_client.get("ha:metadata")
        metadata = json.loads(metadata_data) if metadata_data else {}
        
        # Count cached entities by scanning keys
        entity_pattern = "ha:entity:*"
        entity_keys = []
        async for key in redis_client.scan_iter(match=entity_pattern):
            entity_keys.append(key.decode('utf-8'))
        
        # Get domain information
        domain_counts = {}
        for key in entity_keys:
            entity_id = key.replace('ha:entity:', '')
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Check for controllable entities cache
        controllable_data = await redis_client.get("ha:entities")
        controllable_count = 0
        if controllable_data:
            try:
                controllable_entities = json.loads(controllable_data)
                controllable_count = len(controllable_entities) if isinstance(controllable_entities, list) else 0
            except json.JSONDecodeError:
                pass
        
        await redis_client.aclose()
        
        return {
            "cache_metadata": metadata,
            "cached_entities": {
                "total_count": len(entity_keys),
                "domain_breakdown": domain_counts,
                "controllable_count": controllable_count
            },
            "cache_keys": {
                "entity_keys_sample": entity_keys[:10],  # Show first 10 as sample
                "total_entity_keys": len(entity_keys)
            },
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in get_ha_cache_info: {traceback.format_exc()}")
        
        logger.error(f"Error getting cache info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cache info: {str(e)}"
        )