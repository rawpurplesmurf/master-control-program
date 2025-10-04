import json
import logging
import httpx
from datetime import datetime
from typing import List, Dict, Any
from fastapi import HTTPException

from mcp.config import settings
from mcp.cache import redis_client

logger = logging.getLogger(__name__)

def create_ollama_prompt(command: str, entities: Dict[str, str], rules: List[Dict[str, Any]]) -> str:
    system_prompt = (
        "You are a helpful and efficient Home Assistant AI. "
        "Your sole purpose is to translate natural language commands into a structured JSON array. "
        "Each object represents a single action or a state check. "
        "The current date and time is: {current_time}. "
        "Here is a list of all available entities and their friendly names: {entities}. "
        "You must use the entity IDs from this list. "
        "If a command is conditional (e.g., 'if it's dark'), you must include a 'check_state' action. "
    ).format(current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), entities=json.dumps(entities))
    user_prompt = f"The user command is: '{command}'."
    response_schema = """
    [
      {
        "type": "action" | "check_state",
        "intent": "string",
        "entity_id": "string",
        "data": "object"
      }
    ]
    """
    return f"{system_prompt}\n{user_prompt}\n\nReturn ONLY the JSON array matching this schema:\n{response_schema}"

async def call_ollama_text(prompt: str) -> str:
    """Call Ollama for natural language text response (not structured JSON)."""
    logger.info(f"Calling Ollama for text response with model: {settings.OLLAMA_MODEL}")
    logger.debug(f"Prompt length: {len(prompt)} characters")
    
    # Check cache first
    cache_key = f"text:{prompt}"
    cached_response = await redis_client.get(cache_key)
    if cached_response:
        logger.info("Found cached response for Ollama text request")
        return cached_response.decode('utf-8')

    logger.info(f"No cache hit, sending request to Ollama at {settings.OLLAMA_URL}")
    try:
        async with httpx.AsyncClient() as client:
            ollama_request = {
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
                # No "format": "json" for natural language responses
            }
            logger.debug(f"Ollama request payload: {json.dumps(ollama_request, indent=2)}")
            
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json=ollama_request,
                timeout=60
            )
            logger.info(f"Ollama API response status: {response.status_code}")
            response.raise_for_status()
            
            full_response = response.json()
            response_text = full_response['response']
            logger.info(f"Received Ollama response, length: {len(response_text)} characters")
            logger.debug(f"Ollama response preview: {response_text[:200]}...")
            
            # Cache the response
            await redis_client.set(cache_key, response_text, ex=3600)  # Cache for 1 hour
            logger.info("Cached Ollama response for 1 hour")

            return response_text
    except httpx.HTTPStatusError as e:
        # Log the error for debugging
        print(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Ollama API error: {e.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama call failed: {str(e)}")

async def call_ollama(prompt: str) -> List[Dict[str, Any]]:
    # Check cache first
    cached_response = await redis_client.get(prompt)
    if cached_response:
        return json.loads(cached_response)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OLLAMA_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            response.raise_for_status()
            full_response = response.json()
            response_text = full_response['response']
            # The response from Ollama with format="json" is a string that needs to be parsed.
            json_response = json.loads(response_text)
            
            # Cache the response
            await redis_client.set(prompt, json.dumps(json_response), ex=3600) # Cache for 1 hour

            return json_response
    except httpx.HTTPStatusError as e:
        # Log the error for debugging
        print(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Ollama API error: {e.response.text}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Ollama returned an invalid JSON response.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama call failed: {str(e)}")
