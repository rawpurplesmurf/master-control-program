from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
import datetime

from mcp import schemas, models
from mcp.database import get_db
from mcp.ollama import create_ollama_prompt, call_ollama
from mcp.action_executor import execute_actions
from mcp.health_checks import (
    check_mysql_connection,
    check_redis_connection,
    check_home_assistant_connection,
    check_ollama_connection,
)

router = APIRouter()

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
        "system_prompt": template.system_prompt,
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

import json
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Optional

from mcp import schemas, models
from mcp.database import get_db
from mcp.ollama import create_ollama_prompt, call_ollama

from mcp.action_executor import execute_actions
from mcp.health_checks import (
    check_mysql_connection,
    check_redis_connection,
    check_home_assistant_connection,
    check_ollama_connection,
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

# --- Rules CRUD Endpoints ---
@router.get("/api/rules", response_model=List[schemas.RuleOut])
def list_rules(db: Session = Depends(get_db), rule_type: Optional[str] = None):
    """Get all rules, optionally filtered by type (skippy_guardrail or submind_automation)"""
    query = db.query(models.Rule)
    if rule_type:
        query = query.filter(models.Rule.rule_type == rule_type)
    rules = query.all()
    
    # Parse JSON fields for response
    for rule in rules:
        rule.blocked_actions = json.loads(rule.blocked_actions or '[]')
        rule.guard_conditions = json.loads(rule.guard_conditions or '{}')
        rule.trigger_conditions = json.loads(rule.trigger_conditions or '{}')
        rule.target_actions = json.loads(rule.target_actions or '[]')
    
    return rules

@router.get("/api/rules/{rule_id}", response_model=schemas.RuleOut)
def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific rule by ID"""
    rule = db.query(models.Rule).filter(models.Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Parse JSON fields
    rule.blocked_actions = json.loads(rule.blocked_actions or '[]')
    rule.guard_conditions = json.loads(rule.guard_conditions or '{}')
    rule.trigger_conditions = json.loads(rule.trigger_conditions or '{}')
    rule.target_actions = json.loads(rule.target_actions or '[]')
    
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
        
        # Parse JSON fields for response
        db_rule.blocked_actions = json.loads(db_rule.blocked_actions or '[]')
        db_rule.guard_conditions = json.loads(db_rule.guard_conditions or '{}')
        db_rule.trigger_conditions = json.loads(db_rule.trigger_conditions or '{}')
        db_rule.target_actions = json.loads(db_rule.target_actions or '[]')
        
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
        
        # Parse JSON fields for response
        db_rule.blocked_actions = json.loads(db_rule.blocked_actions or '[]')
        db_rule.guard_conditions = json.loads(db_rule.guard_conditions or '{}')
        db_rule.trigger_conditions = json.loads(db_rule.trigger_conditions or '{}')
        db_rule.target_actions = json.loads(db_rule.target_actions or '[]')
        
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

@router.post("/api/command", response_model=schemas.CommandSuccess, responses={400: {"model": schemas.CommandError}, 500: {"model": schemas.CommandError}})
async def process_command(command_input: schemas.CommandInput, db: Session = Depends(get_db)):
    try:
        # 1. Retrieve entities and rules
        entities = db.query(models.Entity).all()
        rules = db.query(models.Rule).all()
        entity_dict = {e.friendly_name: e.entity_id for e in entities}
        rules_list = [{
            "rule_name": r.rule_name,
            "trigger_entity": r.trigger_entity,
            "target_entity": r.target_entity,
            "override_keywords": r.override_keywords.split(',') if r.override_keywords else []
        } for r in rules]

        # 2. Create prompt and call Ollama
        prompt = create_ollama_prompt(command_input.command, entity_dict, rules_list)
        ollama_response = await call_ollama(prompt)

        # 3. Process and execute actions
        executed_actions = await execute_actions(ollama_response, rules_list, command_input.command)

        # 4. Log history
        history_entry = models.PromptHistory(
            user_command=command_input.command,
            ollama_response=json.dumps(ollama_response),
            executed_actions=json.dumps([action.dict() for action in executed_actions]),
            status="success"
        )
        db.add(history_entry)
        db.commit()

        return schemas.CommandSuccess(message="Command executed successfully.", executed_actions=executed_actions)

    except HTTPException as e:
        db.rollback()
        # Log failure
        history_entry = models.PromptHistory(user_command=command_input.command, ollama_response=getattr(e, 'detail', '{}'), executed_actions="[]", status="failed")
        db.add(history_entry)
        db.commit()
        raise e
    except Exception as e:
        db.rollback()
        # Log failure
        history_entry = models.PromptHistory(user_command=command_input.command, ollama_response="{}", executed_actions="[]", status="failed")
        db.add(history_entry)
        db.commit()
        # It's good practice to not expose raw exception details to the client
        # In a production environment, log the full error `e` for debugging
        raise HTTPException(status_code=500, detail="An internal error occurred.")