"""
Command processing pipeline for the Master Control Program.

This module handles the complete flow from natural language command
to LLM response via prompt templates and data fetchers.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from mcp import models
from mcp.data_fetcher_engine import get_prefetch_data
from mcp.ollama import call_ollama_text
from mcp.prompt_history import prompt_history_manager

logger = logging.getLogger(__name__)

def determine_prompt_template(command: str) -> str:
    """
    Determine which prompt template to use for the command.
    For now, hardcoded to 'default'.
    
    TODO: Implement intent matching logic that:
    - Analyzes command text against template intent_keywords
    - Returns the best matching template name
    - Falls back to 'default' if no good match found
    """
    logger.info(f"Determining prompt template for command: {command[:50]}...")
    
    # Hardcoded for now - will implement intent matching later
    template_name = "default"
    
    logger.info(f"Selected template: {template_name}")
    return template_name

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
    
    Args:
        template: The prompt template to use
        context: Dictionary with user_input and fetched data
        
    Returns:
        Tuple of (system_prompt, formatted_user_prompt)
    """
    try:
        # Format the user template with context data
        formatted_user_prompt = template.user_template.format(**context)
        system_prompt = template.system_prompt
        
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
        # Step 1: Determine prompt template (hardcoded for now)
        template_name = determine_prompt_template(command)
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