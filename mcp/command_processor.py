"""
Command processing pipeline for the Master Control Program.

This module handles the complete flow from natural language command
to LLM response via prompt templates and data fetchers.
"""

import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from mcp import models
from mcp.database import get_db
from mcp.data_fetcher_engine import get_prefetch_data
from mcp.ollama import call_ollama_text
from mcp.prompt_history import prompt_history_manager

logger = logging.getLogger(__name__)

def determine_prompt_template(command: str, db: Session) -> str:
    """
    Determine which prompt template to use based on intent keywords.
    
    Analyzes the first 5 words of the command against all template intent_keywords.
    Returns the best matching template name, or 'default' if no match found.
    
    Args:
        command: The user's natural language command
        db: Database session to query templates
        
    Returns:
        Template name to use for processing
    """
    logger.info(f"Analyzing command for template selection: {command[:50]}...")
    
    # Extract first 5 words from command (case-insensitive)
    command_words = command.lower().strip().split()[:5]
    logger.debug(f"First 5 words: {command_words}")
    
    if not command_words:
        logger.warning("Empty command, using default template")
        return "default"
    
    try:
        # Get all active prompt templates from database
        templates = db.query(models.PromptTemplate).all()
        
        if not templates:
            logger.warning("No prompt templates found in database")
            return "default"
        
        # Score each template based on keyword matches
        template_scores = []
        
        for template in templates:
            score = 0
            matched_keywords = []
            
            # Parse intent keywords (comma-separated, case-insensitive)
            if template.intent_keywords:
                intent_keywords = [kw.strip().lower() for kw in template.intent_keywords.split(',')]
                
                # Check each intent keyword against command words
                for keyword in intent_keywords:
                    if keyword in command_words:
                        score += 1
                        matched_keywords.append(keyword)
                        logger.debug(f"Template '{template.template_name}' matched keyword: '{keyword}'")
            
            if score > 0:
                template_scores.append({
                    'template_name': template.template_name,
                    'score': score,
                    'matched_keywords': matched_keywords
                })
        
        # Sort by score (highest first), then by number of total keywords (more specific templates first)
        if template_scores:
            # Add total keyword count for tie-breaking
            for score_item in template_scores:
                template = next(t for t in templates if t.template_name == score_item['template_name'])
                total_keywords = len([kw.strip() for kw in template.intent_keywords.split(',')]) if template.intent_keywords else 0
                score_item['total_keywords'] = total_keywords
            
            # Sort by score first (highest), then by total keywords (highest = more specific)
            template_scores.sort(key=lambda x: (x['score'], x['total_keywords']), reverse=True)
            best_match = template_scores[0]
            
            logger.info(f"Selected template: '{best_match['template_name']}' "
                       f"(score: {best_match['score']}, "
                       f"matched: {best_match['matched_keywords']}, "
                       f"total_keywords: {best_match['total_keywords']})")
            
            return best_match['template_name']
        
        # No keyword matches found, use default
        logger.info("No keyword matches found, using default template")
        return "default"
        
    except Exception as e:
        logger.error(f"Error in template selection: {str(e)}")
        logger.info("Falling back to default template due to error")
        return "default"

def execute_data_fetchers(template: models.PromptTemplate, command: str) -> Dict[str, Any]:
    """
    Execute all data fetchers required by the prompt template.
    
    Args:
        template: The prompt template with pre_fetch_data requirements
        command: The original user command
        
    Returns:
        Dict containing fetched data keyed by fetcher name
    """
    logger.info(f"Starting data fetcher execution for template: {template.template_name}")
    
    context = {"user_input": command, "user_command": command}
    
    # Parse pre_fetch_data from JSON string
    fetcher_keys = []
    if template.pre_fetch_data:
        try:
            parsed_data = json.loads(template.pre_fetch_data)
            if isinstance(parsed_data, list):
                fetcher_keys = parsed_data
            elif isinstance(parsed_data, dict):
                fetcher_keys = list(parsed_data.keys())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse pre_fetch_data JSON: {e}")
            return context
    
    if not fetcher_keys:
        logger.info("No data fetchers required for this template")
        return context
    
    logger.info(f"Executing {len(fetcher_keys)} data fetchers for template: {template.template_name}")
    
    for fetcher_key in fetcher_keys:
        logger.info(f"Fetching data for: {fetcher_key}")
        try:
            fetched_data = get_prefetch_data(fetcher_key)
            context[fetcher_key] = fetched_data
            
            # Log fetch status
            if isinstance(fetched_data, dict) and fetched_data.get('failed_fetch'):
                logger.warning(f"Data fetch failed for {fetcher_key}: {fetched_data.get('error', 'Unknown error')}")
            else:
                logger.info(f"Successfully fetched data for {fetcher_key}")
                
        except Exception as e:
            logger.error(f"Exception while fetching {fetcher_key}: {str(e)}")
            context[fetcher_key] = {'failed_fetch': True, 'error': str(e)}
    
    logger.info(f"Data fetching completed. Context keys: {list(context.keys())}")
    return context

def construct_prompt(template: models.PromptTemplate, context: Dict[str, Any]) -> tuple[str, str]:
    """
    Construct the system and user prompts with fetched data.
    
    Supports several types of placeholder substitutions:
    - {variable_name} - Replaced with context variables from data fetchers
    - [skippy_guard_rail:name] - Replaced with rule data from skippy guardrails
      (note: this references a rule with rule_name='skippy_guard_rail_name')
    - [system_prompt:name] - Replaced with content from stored system prompts
    
    Args:
        template: The prompt template to use
        context: Dictionary with user_input and fetched data
        
    Returns:
        Tuple of (system_prompt, formatted_user_prompt)
    """
    try:
        # Format the user template with context data
        formatted_user_prompt = template.user_template.format(**context)
        
        # Process any skippy guardrail placeholders in the format [skippy_guard_rail:name]
        import re
        guardrail_placeholders = re.findall(r'\[skippy_guard_rail:([^\]]+)\]', formatted_user_prompt)
        
        # Replace each guardrail placeholder with actual rule data
        for rule_name in guardrail_placeholders:
            full_rule_name = f"skippy_guard_rail_{rule_name}"
            db = next(get_db())
            rule = db.query(models.Rule).filter(
                models.Rule.rule_name == full_rule_name,
                models.Rule.rule_type == "skippy_guardrail"
            ).first()
            
            if rule:
                rule_text = f"GUARD RAIL: {rule.description}\n"
                rule_text += f"• Target: {rule.target_entity_pattern}\n"
                rule_text += f"• Blocked Actions: {rule.blocked_actions}\n"
                rule_text += f"• Conditions: {rule.guard_conditions}\n"
                if rule.override_keywords:
                    rule_text += f"• Override with: {rule.override_keywords}\n"
                
                # Replace placeholder with rule data
                formatted_user_prompt = formatted_user_prompt.replace(f"[skippy_guard_rail:{rule_name}]", rule_text)
            else:
                # If rule not found, leave a note
                formatted_user_prompt = formatted_user_prompt.replace(
                    f"[skippy_guard_rail:{rule_name}]", 
                    f"[Guard rail '{full_rule_name}' not found]"
                )
        
        # Get system prompt - either from template or from system_prompts table
        system_prompt = template.system_prompt
        
        # Look for system prompt placeholders in the format [system_prompt:name]
        system_placeholders = re.findall(r'\[system_prompt:([^\]]+)\]', system_prompt)
        if system_placeholders:
            # Attempt to load the system prompt from the database
            for prompt_name in system_placeholders:
                db = next(get_db())
                db_prompt = db.query(models.SystemPrompt).filter(
                    models.SystemPrompt.name == prompt_name
                ).first()
                
                if db_prompt:
                    # Replace the placeholder with the actual system prompt
                    system_prompt = system_prompt.replace(f"[system_prompt:{prompt_name}]", db_prompt.prompt)
                else:
                    # If not found, leave a note
                    system_prompt = system_prompt.replace(
                        f"[system_prompt:{prompt_name}]", 
                        f"[System prompt '{prompt_name}' not found]"
                    )
        
        logger.info(f"Successfully constructed prompt for template: {template.template_name}")
        logger.debug(f"System prompt length: {len(system_prompt)}")
        logger.debug(f"User prompt length: {len(formatted_user_prompt)}")
        
        return system_prompt, formatted_user_prompt
        
    except KeyError as e:
        error_msg = f"Missing placeholder {e} in template {template.template_name}"
        logger.error(error_msg)
        # Return a fallback prompt that explains the error
        return (
            "You are a helpful assistant. There was an error with the prompt template.",
            f"Error constructing prompt: {error_msg}. Original user input: {context.get('user_input', 'N/A')}"
        )
    except Exception as e:
        error_msg = f"Unexpected error constructing prompt: {str(e)}"
        logger.error(error_msg)
        return (
            "You are a helpful assistant. There was an error with the prompt template.",
            f"Error: {error_msg}. Original user input: {context.get('user_input', 'N/A')}"
        )

async def process_command_pipeline(command: str, db: Session, source: str = "api") -> Dict[str, Any]:
    """
    Complete command processing pipeline:
    1. Determine prompt template (hardcoded to 'default' for now)
    2. Execute required data fetchers  
    3. Construct prompt with fetched data
    4. Send to LLM
    5. Return structured response
    
    Args:
        command: The natural language command from the user
        db: Database session for template lookup
        
    Returns:
        Dictionary with response and metadata
    """
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Determine prompt template using intelligent keyword matching
        template_name = determine_prompt_template(command, db)
        logger.info(f"Using prompt template: {template_name}")
        
        # Look up the template in database
        template = db.query(models.PromptTemplate).filter(
            models.PromptTemplate.template_name == template_name
        ).first()
        
        if not template:
            logger.error(f"Prompt template '{template_name}' not found in database")
            return {
                "response": f"Error: Prompt template '{template_name}' not found. Please create a 'default' template first.",
                "error": "template_not_found",
                "template_requested": template_name,
                "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                "success": False
            }
        
        # Step 2: Execute data fetchers
        logger.info(f"Template '{template_name}' requires data fetchers: {template.pre_fetch_data}")
        context = execute_data_fetchers(template, command)
        
        # Parse fetcher keys for response metadata
        fetcher_keys = []
        if template.pre_fetch_data:
            try:
                parsed_data = json.loads(template.pre_fetch_data)
                if isinstance(parsed_data, list):
                    fetcher_keys = parsed_data
                elif isinstance(parsed_data, dict):
                    fetcher_keys = list(parsed_data.keys())
            except json.JSONDecodeError:
                fetcher_keys = []
        
        # Step 3: Construct prompt
        system_prompt, user_prompt = construct_prompt(template, context)
        
        logger.info(f"Sending constructed prompt to LLM")
        logger.debug(f"System prompt: {system_prompt[:100]}...")
        logger.debug(f"User prompt: {user_prompt[:100]}...")
        
        # Step 4: Send to LLM (combine prompts as Ollama expects single prompt)
        combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}"
        llm_response = await call_ollama_text(combined_prompt)
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Store prompt history
        metadata = {
            "template_used": template_name,
            "data_fetchers_executed": fetcher_keys,
            "processing_time_ms": processing_time,
            "context_keys": list(context.keys()),
            "command": command
        }
        
        interaction_id = await prompt_history_manager.store_prompt_interaction(
            prompt=combined_prompt,
            response=llm_response,
            source=source,
            metadata=metadata
        )
        
        logger.info(f"Command processing completed successfully in {processing_time}ms, stored as {interaction_id}")
        
        # Step 5: Return structured response
        return {
            "response": llm_response,
            "template_used": template_name,
            "data_fetchers_executed": fetcher_keys,
            "processing_time_ms": processing_time,
            "context_keys": list(context.keys()),
            "interaction_id": interaction_id,
            "success": True
        }
        
    except Exception as e:
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Log full stack trace to debug.log
        import traceback
        debug_logger = logging.getLogger('debug')
        debug_logger.error(f"Exception in command processing pipeline for '{command}': {traceback.format_exc()}")
        
        logger.error(f"Error in command processing pipeline: {str(e)}", exc_info=True)
        
        # Store error in prompt history too
        error_response = f"Error: {str(e)}"
        try:
            metadata = {
                "processing_time_ms": processing_time,
                "error": str(e),
                "command": command
            }
            
            # Only store if we have a prompt to store
            if 'combined_prompt' in locals():
                await prompt_history_manager.store_prompt_interaction(
                    prompt=combined_prompt,
                    response=error_response,
                    source=source,
                    metadata=metadata
                )
        except Exception as history_error:
            logger.error(f"Failed to store error in prompt history: {history_error}")
        
        return {
            "response": f"I apologize, but I encountered an error processing your command: {str(e)}",
            "error": "processing_error",
            "error_details": str(e),
            "processing_time_ms": processing_time,
            "success": False
        }