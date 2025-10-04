# --- Imports ---
# --- Imports ---
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
class PromptTemplateBase(BaseModel):
    template_name: str
    intent_keywords: str
    system_prompt: str
    user_template: str
    pre_fetch_data: List[str]

class PromptTemplateCreate(PromptTemplateBase):
    pass

class PromptTemplateUpdate(BaseModel):
    template_name: Optional[str] = None
    intent_keywords: Optional[str] = None
    system_prompt: Optional[str] = None
    user_template: Optional[str] = None
    pre_fetch_data: Optional[List[str]] = None

class PromptTemplateOut(PromptTemplateBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Data Fetcher CRUD schemas
class DataFetcherBase(BaseModel):
    fetcher_key: str
    description: str
    ttl_seconds: int = 300
    python_code: str
    is_active: bool = True

class DataFetcherCreate(DataFetcherBase):
    pass

class DataFetcherUpdate(BaseModel):
    fetcher_key: Optional[str] = None
    description: Optional[str] = None
    ttl_seconds: Optional[int] = None
    python_code: Optional[str] = None
    is_active: Optional[bool] = None

class DataFetcherOut(DataFetcherBase):
    id: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# Rule CRUD schemas
class RuleBase(BaseModel):
    rule_name: str
    rule_type: str  # 'skippy_guardrail' or 'submind_automation'
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 0

class SkippyGuardrailCreate(RuleBase):
    rule_type: str = "skippy_guardrail"
    target_entity_pattern: Optional[str] = None
    blocked_actions: Optional[List[str]] = None
    guard_conditions: Optional[Dict[str, Any]] = None
    override_keywords: Optional[str] = None

class SubmindAutomationCreate(RuleBase):
    rule_type: str = "submind_automation"
    trigger_conditions: Optional[Dict[str, Any]] = None
    target_actions: Optional[List[Dict[str, Any]]] = None
    execution_schedule: Optional[str] = None

class RuleCreate(BaseModel):
    rule_name: str
    rule_type: str  # 'skippy_guardrail' or 'submind_automation'
    description: Optional[str] = None
    is_active: bool = True
    priority: int = 0
    
    # Skippy Guardrail fields
    target_entity_pattern: Optional[str] = None
    blocked_actions: Optional[List[str]] = None
    guard_conditions: Optional[Dict[str, Any]] = None
    override_keywords: Optional[str] = None
    
    # Submind Automation fields
    trigger_conditions: Optional[Dict[str, Any]] = None
    target_actions: Optional[List[Dict[str, Any]]] = None
    execution_schedule: Optional[str] = None

class RuleUpdate(BaseModel):
    rule_name: Optional[str] = None
    rule_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    
    # Skippy Guardrail fields
    target_entity_pattern: Optional[str] = None
    blocked_actions: Optional[List[str]] = None
    guard_conditions: Optional[Dict[str, Any]] = None
    override_keywords: Optional[str] = None
    
    # Submind Automation fields
    trigger_conditions: Optional[Dict[str, Any]] = None
    target_actions: Optional[List[Dict[str, Any]]] = None
    execution_schedule: Optional[str] = None

class RuleOut(BaseModel):
    id: int
    rule_name: str
    rule_type: str
    description: Optional[str] = None
    is_active: bool
    priority: int
    
    # Skippy Guardrail fields
    target_entity_pattern: Optional[str] = None
    blocked_actions: Optional[List[str]] = None
    guard_conditions: Optional[Dict[str, Any]] = None
    override_keywords: Optional[str] = None
    
    # Submind Automation fields
    trigger_conditions: Optional[Dict[str, Any]] = None
    target_actions: Optional[List[Dict[str, Any]]] = None
    execution_schedule: Optional[str] = None
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    last_executed: Optional[str] = None
    execution_count: Optional[int] = 0
    
    @classmethod
    def from_orm(cls, obj):
        # Convert datetime fields to strings for JSON serialization
        data = obj.__dict__.copy()
        for field in ['created_at', 'updated_at', 'last_executed']:
            if hasattr(obj, field) and getattr(obj, field):
                dt_value = getattr(obj, field)
                if hasattr(dt_value, 'isoformat'):
                    data[field] = dt_value.isoformat()
        return cls(**data)

    class Config:
        from_attributes = True
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class CommandInput(BaseModel):
    command: str
    source: Optional[str] = "api"

# Prompt History schemas
class PromptHistoryOut(BaseModel):
    id: str
    prompt: str
    response: str
    source: str
    timestamp: str
    metadata: Dict[str, Any]

class PromptHistoryStats(BaseModel):
    total_interactions: int
    source_distribution: Dict[str, int]
    recent_count: int

class PromptRerunRequest(BaseModel):
    interaction_id: str

class PromptRerunResponse(BaseModel):
    success: bool
    new_interaction_id: Optional[str] = None
    original_interaction_id: Optional[str] = None
    response: Optional[str] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    source: Optional[str] = "api"

class ExecutedAction(BaseModel):
    service: str
    entity_id: str
    data: Dict[str, Any]

class CommandSuccess(BaseModel):
    status: str = "success"
    message: str
    executed_actions: List[ExecutedAction]

class CommandError(BaseModel):
    status: str = "error"
    message: str