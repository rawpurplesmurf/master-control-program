"""
Enhanced Action Executor with Home Assistant device control capabilities.
Handles service calls, state validation, and action logging.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import httpx

from mcp.config import settings
from mcp.cache import get_redis_client
from mcp.ha_state import get_ha_entity, get_ha_entities
from mcp.ha_services import validate_ha_service

logger = logging.getLogger(__name__)

class HomeAssistantActionExecutor:
    """Executes actions on Home Assistant devices with validation and logging."""
    
    def __init__(self):
        self.base_url = settings.HA_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {settings.HA_TOKEN}",
            "Content-Type": "application/json"
        }
        self.redis_client = None
    
    async def _get_redis_client(self):
        """Get Redis client for action logging."""
        if not self.redis_client:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    async def execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Home Assistant action.
        
        Args:
            action: Action dictionary with 'service', 'entity_id', and optional 'data'
            
        Returns:
            Execution result with success status and details
        """
        try:
            # Validate action structure
            if not self._validate_action(action):
                return {
                    "success": False,
                    "error": "Invalid action format",
                    "action": action
                }
            
            service = action['service']
            entity_id = action.get('entity_id')
            service_data = action.get('data', {})
            
            # Add entity_id to service data if provided
            if entity_id:
                service_data['entity_id'] = entity_id
            
            # Validate service exists in Home Assistant
            service_validation = await validate_ha_service(service)
            if not service_validation['valid']:
                return {
                    "success": False,
                    "error": service_validation['error'],
                    "service": service,
                    "available_services": service_validation.get('available_services', [])
                }
            
            # Validate entity exists and is controllable (if entity_id provided)
            if entity_id:
                entity_validation = await self._validate_entity(entity_id, service)
                if not entity_validation['valid']:
                    return {
                        "success": False,
                        "error": entity_validation['error'],
                        "entity_id": entity_id,
                        "service": service
                    }
            
            # Get current state for comparison
            old_state = None
            if entity_id:
                old_state = await get_ha_entity(entity_id)
            
            # Execute the service call
            result = await self._call_ha_service(service, service_data)
            
            if result['success']:
                # Log the action
                await self._log_action(action, result, old_state)
                
                # Schedule entity state refresh 5 seconds after successful action
                if entity_id:
                    asyncio.create_task(self._refresh_entity_state(entity_id, delay_seconds=5))
                    logger.info(f"🕐 Scheduled state refresh for {entity_id} in 5 seconds")
                
                logger.info(f"✅ Successfully executed {service} on {entity_id}")
                return {
                    "success": True,
                    "service": service,
                    "entity_id": entity_id,
                    "data": service_data,
                    "ha_response": result.get('response'),
                    "service_info": service_validation.get('service_info'),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            else:
                logger.error(f"❌ Failed to execute {service} on {entity_id}: {result.get('error')}")
                return {
                    "success": False,
                    "error": f"Home Assistant service call failed: {result.get('error')}",
                    "service": service,
                    "entity_id": entity_id
                }
                
        except Exception as e:
            # Log full stack trace to debug.log
            import traceback
            debug_logger = logging.getLogger('debug')
            debug_logger.error(f"Exception in execute_action for {action}: {traceback.format_exc()}")
            
            logger.error(f"Error executing action: {e}")
            return {
                "success": False,
                "error": f"Action execution error: {str(e)}",
                "action": action
            }
    
    def _validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate action has required fields."""
        if not isinstance(action, dict):
            debug_logger = logging.getLogger('debug')
            debug_logger.error(f"Invalid action - not a dict: {type(action)} = {action}")
            return False
        
        if 'service' not in action:
            debug_logger = logging.getLogger('debug')
            debug_logger.error(f"Invalid action - missing 'service' field: {action}")
            return False
            
        service = action['service']
        if not isinstance(service, str) or '.' not in service:
            debug_logger = logging.getLogger('debug')
            debug_logger.error(f"Invalid action - service format invalid: service={service}, type={type(service)}")
            return False
            
        return True
    
    async def _validate_entity(self, entity_id: str, service: str) -> Dict[str, Any]:
        """Validate entity exists and is controllable."""
        try:
            # Check if entity exists
            entity = await get_ha_entity(entity_id)
            if not entity:
                return {
                    "valid": False,
                    "error": f"Entity {entity_id} not found or not available"
                }
            
            # Check if entity is in controllable entities
            controllable = await get_ha_entities()
            if not any(e.get('entity_id') == entity_id for e in controllable):
                return {
                    "valid": False,
                    "error": f"Entity {entity_id} is not controllable"
                }
            
            return {"valid": True}
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Entity validation error: {str(e)}"
            }
    
    async def _call_ha_service(self, service: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make the actual Home Assistant service call."""
        try:
            # Parse service domain and name
            service_parts = service.split('.')
            if len(service_parts) != 2:
                return {
                    "success": False,
                    "error": f"Invalid service format: {service}. Expected format: domain.service"
                }
            
            domain, service_name = service_parts
            url = f"{self.base_url}/api/services/{domain}/{service_name}"
            
            logger.info(f"🔄 Calling HA service: {service} with data: {service_data}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=service_data
                )
                
                if response.status_code == 200:
                    response_data = response.json()
                    return {
                        "success": True,
                        "response": response_data,
                        "status_code": response.status_code
                    }
                else:
                    error_text = response.text
                    logger.error(f"HA service call failed: {response.status_code} - {error_text}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {error_text}",
                        "status_code": response.status_code
                    }
                    
        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Home Assistant service call timed out"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Service call error: {str(e)}"
            }
    
    async def _log_action(self, action: Dict[str, Any], result: Dict[str, Any], old_state: Optional[Dict[str, Any]]):
        """Log action execution to Redis."""
        try:
            redis_client = await self._get_redis_client()
            
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "action": action,
                "result": result,
                "old_state": old_state,
                "success": result.get('success', False)
            }
            
            # Log to entity-specific action log (7-day retention)
            entity_id = action.get('entity_id')
            if entity_id:
                log_key = f"ha:actions:{entity_id}"
                timestamp_score = datetime.utcnow().timestamp()
                
                await redis_client.zadd(log_key, {json.dumps(log_entry): timestamp_score})
                await redis_client.expire(log_key, 604800)  # 7 days
                
                # Clean up old entries
                cutoff_timestamp = timestamp_score - 604800
                await redis_client.zremrangebyscore(log_key, 0, cutoff_timestamp)
            
            # Global action log
            global_log_key = "ha:actions:all"
            timestamp_score = datetime.utcnow().timestamp()
            await redis_client.zadd(global_log_key, {json.dumps(log_entry): timestamp_score})
            await redis_client.expire(global_log_key, 604800)  # 7 days
            
            logger.debug(f"📝 Logged action for {entity_id}")
            
        except Exception as e:
            logger.error(f"Error logging action: {e}")

    async def get_action_history(self, entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get action history for an entity."""
        try:
            redis_client = await self._get_redis_client()
            log_key = f"ha:actions:{entity_id}"
            
            # Get recent actions (newest first)
            log_entries = await redis_client.zrevrange(log_key, 0, limit-1)
            
            parsed_entries = []
            for entry in log_entries:
                try:
                    parsed_entry = json.loads(entry)
                    parsed_entries.append(parsed_entry)
                except json.JSONDecodeError:
                    continue
            
            return parsed_entries
            
        except Exception as e:
            logger.error(f"Error getting action history for {entity_id}: {e}")
            return []
    
    async def _refresh_entity_state(self, entity_id: str, delay_seconds: int = 5):
        """
        Force refresh of a specific entity's state in Redis cache after an action.
        
        Args:
            entity_id: The entity to refresh
            delay_seconds: Seconds to wait before refreshing (default: 5)
        """
        try:
            # Wait for Home Assistant to process the state change
            await asyncio.sleep(delay_seconds)
            
            logger.info(f"🔄 Force refreshing state for {entity_id} after action")
            
            # Fetch fresh state from Home Assistant REST API
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/states/{entity_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    fresh_state = response.json()
                    logger.info(f"✅ Got fresh state for {entity_id}: {fresh_state.get('state')}")
                    
                    # Update Redis cache with fresh state
                    await self._update_entity_cache(entity_id, fresh_state)
                    
                    logger.info(f"📝 Updated Redis cache for {entity_id} with new state: {fresh_state.get('state')}")
                    
                elif response.status_code == 404:
                    logger.warning(f"⚠️ Entity {entity_id} not found in Home Assistant")
                else:
                    logger.warning(f"⚠️ Failed to fetch fresh state for {entity_id}: HTTP {response.status_code}")
                    
        except Exception as e:
            logger.error(f"❌ Error refreshing state for {entity_id}: {e}")
    
    async def _update_entity_cache(self, entity_id: str, entity_data: Dict[str, Any]):
        """
        Update Redis cache with fresh entity data.
        
        Args:
            entity_id: The entity ID
            entity_data: Fresh entity data from Home Assistant API
        """
        try:
            redis_client = await self._get_redis_client()
            
            # Store in individual entity cache with 30 minute TTL
            entity_key = f"ha:entity:{entity_id}"
            await redis_client.setex(
                entity_key, 
                1800,  # 30 minutes TTL 
                json.dumps(entity_data)
            )
            logger.debug(f"📝 Cached individual entity {entity_id}")
            
            # Update the main entities list cache if it exists
            entities_key = "ha:all_states"
            entities_json = await redis_client.get(entities_key)
            
            if entities_json:
                try:
                    entities = json.loads(entities_json)
                    
                    # Find and update the entity in the list
                    entity_updated = False
                    for i, entity in enumerate(entities):
                        if entity.get('entity_id') == entity_id:
                            entities[i] = entity_data
                            entity_updated = True
                            logger.debug(f"📝 Updated {entity_id} in entities list cache: {entity_data.get('state')}")
                            break
                    
                    if not entity_updated:
                        # Entity not found in cache, add it
                        entities.append(entity_data)
                        logger.debug(f"📝 Added new entity {entity_id} to entities list cache")
                    
                    # Save updated entities list back to Redis with same TTL
                    await redis_client.setex(
                        entities_key,
                        1800,  # 30 minutes TTL
                        json.dumps(entities)
                    )
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in entities cache, skipping list update")
            
            # Also update controllable entities cache if it exists  
            controllable_key = "ha:entities"
            controllable_json = await redis_client.get(controllable_key)
            
            if controllable_json:
                try:
                    controllable_entities = json.loads(controllable_json)
                    
                    # Check if this entity is in the controllable list
                    for i, entity in enumerate(controllable_entities):
                        if entity.get('entity_id') == entity_id:
                            controllable_entities[i] = entity_data
                            logger.debug(f"📝 Updated {entity_id} in controllable entities cache")
                            
                            # Save back to Redis
                            await redis_client.setex(
                                controllable_key,
                                1800,  # 30 minutes TTL
                                json.dumps(controllable_entities)
                            )
                            break
                            
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in controllable entities cache")
                    
            logger.info(f"✅ Successfully updated all caches for {entity_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating entity cache for {entity_id}: {e}")

# Global action executor instance
_action_executor = HomeAssistantActionExecutor()

async def execute_ha_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a Home Assistant action."""
    return await _action_executor.execute_action(action)

async def get_ha_action_history(entity_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get action history for an entity."""
    return await _action_executor.get_action_history(entity_id, limit)