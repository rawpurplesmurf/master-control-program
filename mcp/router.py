from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
import datetime
import logging

from mcp import schemas, models
from mcp.database import get_db
from mcp.ollama import create_ollama_prompt, call_ollama
from mcp.action_executor import execute_actions
from mcp.prompt_history import prompt_history_manager
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