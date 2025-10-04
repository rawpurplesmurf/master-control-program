
from datetime import datetime
from mcp.database import Base
from sqlalchemy import Column, Integer, String, Text, DateTime
import json

class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_name = Column(String(128), nullable=False)
    intent_keywords = Column(Text, nullable=False)
    system_prompt = Column(Text, nullable=False)
    user_template = Column(Text, nullable=False)
    pre_fetch_data = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

class Entity(Base):
    __tablename__ = 'entities'
    entity_id = Column(String(255), primary_key=True)
    friendly_name = Column(String(255), nullable=False)
    domain = Column(String(50), nullable=False)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)

class Rule(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)  # 'skippy_guardrail' or 'submind_automation'
    
    # Common fields
    description = Column(Text)
    is_active = Column(Integer, default=1)  # Using Integer for boolean compatibility
    priority = Column(Integer, default=0)
    
    # Skippy Guardrail fields
    target_entity_pattern = Column(String(255))
    blocked_actions = Column(Text)  # JSON stored as text
    guard_conditions = Column(Text)  # JSON stored as text
    override_keywords = Column(Text)
    
    # Submind Automation fields
    trigger_conditions = Column(Text)  # JSON stored as text
    target_actions = Column(Text)  # JSON stored as text
    execution_schedule = Column(String(100))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_executed = Column(DateTime)
    execution_count = Column(Integer, default=0)

class PromptHistory(Base):
    __tablename__ = 'prompt_history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    user_command = Column(Text, nullable=False)
    ollama_response = Column(Text, nullable=False)
    executed_actions = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)

class DataFetcher(Base):
    __tablename__ = 'data_fetchers'
    id = Column(Integer, primary_key=True, autoincrement=True)
    fetcher_key = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    ttl_seconds = Column(Integer, nullable=False, default=300)
    python_code = Column(Text, nullable=False)
    is_active = Column(Integer, nullable=False, default=1)  # Use Integer instead of Boolean for compatibility
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)