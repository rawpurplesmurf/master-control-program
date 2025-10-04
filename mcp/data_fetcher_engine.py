"""
Data Fetcher Engine for configurable pre-fetch data mappings.
Supports Redis caching with TTL and safe code execution.
"""

import json
import datetime
import logging
from typing import Dict, Any, Optional
from mcp.cache import get_redis_client
from mcp.database import get_db
from mcp import models

logger = logging.getLogger(__name__)

def get_redis_sync():
    """Get a synchronous Redis client to avoid asyncio issues"""
    import redis
    import os
    
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        host = os.environ.get("REDIS_HOST", "localhost")
        port = os.environ.get("REDIS_PORT", "6379")
        redis_url = f"redis://{host}:{port}/0"
    
    return redis.from_url(redis_url, decode_responses=True)

def get_safe_execution_globals():
    """Return a safe globals dict for code execution"""
    import datetime
    import json
    from mcp.database import get_db
    from mcp import models
    
    return {
        '__builtins__': {
            '__import__': __import__,  # Add __import__ for Python imports
            'len': len,
            'list': list,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'range': range,
            'enumerate': enumerate,
        },
        'datetime': datetime,
        'json': json,
        'get_redis_client': get_redis_sync,  # Use synchronous Redis client
        'get_db': get_db,
        'models': models,
        'next': next,  # For db = next(get_db())
    }

def execute_fetcher_code(code: str) -> Dict[str, Any]:
    """Safely execute data fetcher code and return result"""
    try:
        safe_globals = get_safe_execution_globals()
        local_vars = {}
        
        # Execute the code
        exec(code, safe_globals, local_vars)
        
        # Code should set a 'result' variable
        result = local_vars.get('result', {'error': 'No result returned from fetcher code'})
        
        # Ensure result is a dict
        if not isinstance(result, dict):
            result = {'data': result}
            
        return result
        
    except Exception as e:
        logger.error(f"Error executing fetcher code: {str(e)}")
        return {'failed_fetch': True, 'error': str(e)}

def get_prefetch_data(fetcher_key: str, force_refresh: bool = False) -> Dict[str, Any]:
    """Get data for a specific fetcher key with Redis caching"""
    logger.info(f"Fetching data for: {fetcher_key}")
    
    # Get fetcher config from database
    db = next(get_db())
    try:
        fetcher = db.query(models.DataFetcher).filter(
            models.DataFetcher.fetcher_key == fetcher_key,
            models.DataFetcher.is_active == 1
        ).first()
        
        if not fetcher:
            logger.error(f"Data fetcher not found: {fetcher_key}")
            return {'failed_fetch': True, 'error': f'Unknown fetcher: {fetcher_key}'}
        
        redis_key = f"mcp:prefetch:{fetcher_key}"
        
        # Check cache first (unless force_refresh)
        if not force_refresh:
            try:
                r = get_redis_sync()  # Use synchronous Redis client
                cached = r.get(redis_key)
                if cached:
                    cached_data = json.loads(cached)
                    cache_time = datetime.datetime.fromisoformat(cached_data.get('_cached_at', '1970-01-01'))
                    age_seconds = (datetime.datetime.now() - cache_time).total_seconds()
                    if age_seconds < fetcher.ttl_seconds:
                        logger.info(f"Using cached data for {fetcher_key} (age: {age_seconds:.1f}s)")
                        return cached_data.get('data', {})
            except Exception as e:
                logger.warning(f"Error reading cache for {fetcher_key}: {str(e)}")
        
        # Execute the fetcher code to get fresh data
        logger.info(f"Executing fresh fetch for {fetcher_key}")
        fresh_data = execute_fetcher_code(fetcher.python_code)
        
        # Cache the result with metadata (even if it failed)
        try:
            cache_entry = {
                'data': fresh_data,
                '_cached_at': datetime.datetime.now().isoformat(),
                '_fetcher_key': fetcher_key,
                '_ttl_seconds': fetcher.ttl_seconds
            }
            
            r = get_redis_sync()  # Use synchronous Redis client
            r.setex(redis_key, fetcher.ttl_seconds, json.dumps(cache_entry))
            logger.info(f"Cached result for {fetcher_key} (TTL: {fetcher.ttl_seconds}s)")
            
        except Exception as e:
            logger.warning(f"Error caching data for {fetcher_key}: {str(e)}")
        
        return fresh_data
        
    except Exception as e:
        logger.error(f"Database error for fetcher {fetcher_key}: {str(e)}")
        return {'failed_fetch': True, 'error': f'Database error: {str(e)}'}
    finally:
        db.close()

def process_prompt_with_data(template, user_input: str) -> tuple[str, dict]:
    """Process a prompt template with fetched data"""
    context = {"user_input": user_input, "user_command": user_input}
    
    # Fetch all required data
    for fetcher_key in template.pre_fetch_data:
        logger.info(f"Processing pre-fetch data: {fetcher_key}")
        fetched_data = get_prefetch_data(fetcher_key)
        context[fetcher_key] = fetched_data
        
        # Log if fetch failed
        if fetched_data.get('failed_fetch'):
            logger.warning(f"Failed to fetch {fetcher_key}: {fetched_data.get('error', 'Unknown error')}")
    
    # Basic string substitution using format
    try:
        formatted_prompt = template.user_template.format(**context)
        logger.info(f"Successfully formatted prompt template: {template.template_name}")
        return formatted_prompt, context
    except KeyError as e:
        error_msg = f"Missing placeholder {e} in template"
        logger.error(error_msg)
        return f"Error: {error_msg}", context
    except Exception as e:
        error_msg = f"Error formatting template: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}", context

def get_available_fetchers() -> list:
    """Get list of all available data fetchers"""
    db = next(get_db())
    try:
        fetchers = db.query(models.DataFetcher).filter(models.DataFetcher.is_active == 1).all()
        return [
            {
                "id": f.id,
                "fetcher_key": f.fetcher_key,
                "description": f.description,
                "ttl_seconds": f.ttl_seconds,
                "is_active": f.is_active,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "updated_at": f.updated_at.isoformat() if f.updated_at else None
            }
            for f in fetchers
        ]
    finally:
        db.close()