"""
Redis-based Home Assistant state manager.
Provides clean interface for accessing cached HA state data.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from mcp.cache import get_redis_client

logger = logging.getLogger(__name__)

class HAStateManager:
    """Manager for Home Assistant state data cached in Redis."""
    
    def __init__(self):
        self.redis_client = None
    
    async def _get_redis(self):
        """Get Redis client, initializing if needed."""
        try:
            if not self.redis_client:
                self.redis_client = await get_redis_client()
            # Test the connection
            await self.redis_client.ping()
            return self.redis_client
        except Exception as e:
            logger.error(f"Redis connection failed, recreating: {e}")
            # Recreate the connection
            self.redis_client = await get_redis_client()
            return self.redis_client
    
    async def get_all_entities(self) -> List[Dict[str, Any]]:
        """Get all Home Assistant entities."""
        try:
            redis = await self._get_redis()
            data = await redis.get("ha:all_states")
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"Error getting all entities: {e}")
            return []
    
    async def get_controllable_entities(self) -> List[Dict[str, Any]]:
        """Get entities that can be controlled (for backward compatibility)."""
        try:
            redis = await self._get_redis()
            data = await redis.get("ha:entities")
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"Error getting controllable entities: {e}")
            return []
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific entity by ID."""
        try:
            redis = await self._get_redis()
            entity_key = f"ha:entity:{entity_id}"
            data = await redis.get(entity_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting entity {entity_id}: {e}")
            return None
    
    async def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a specific domain (e.g., 'light', 'switch')."""
        try:
            redis = await self._get_redis()
            domain_key = f"ha:domain:{domain}"
            data = await redis.get(domain_key)
            if data:
                return json.loads(data)
            return []
        except Exception as e:
            logger.error(f"Error getting entities for domain {domain}: {e}")
            return []
    
    async def search_entities(self, 
                            pattern: Optional[str] = None, 
                            domain: Optional[str] = None,
                            state: Optional[str] = None,
                            friendly_name_contains: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search entities by various criteria."""
        try:
            # Start with all entities or domain-specific entities
            if domain:
                entities = await self.get_entities_by_domain(domain)
            else:
                entities = await self.get_all_entities()
            
            if not entities:
                return []
            
            # Apply filters
            filtered = entities
            
            if pattern:
                filtered = [e for e in filtered if pattern.lower() in e.get("entity_id", "").lower()]
            
            if state:
                filtered = [e for e in filtered if e.get("state", "").lower() == state.lower()]
            
            if friendly_name_contains:
                filtered = [
                    e for e in filtered 
                    if friendly_name_contains.lower() in 
                    e.get("attributes", {}).get("friendly_name", "").lower()
                ]
            
            return filtered
            
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    async def get_entities_by_state(self, state_value: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get entities with a specific state value."""
        return await self.search_entities(state=state_value, domain=domain)
    
    async def get_lights_by_state(self, state: str = "on") -> List[Dict[str, Any]]:
        """Get lights with specific state (on/off)."""
        return await self.get_entities_by_state(state, domain="light")
    
    async def get_switches_by_state(self, state: str = "on") -> List[Dict[str, Any]]:
        """Get switches with specific state (on/off)."""
        return await self.get_entities_by_state(state, domain="switch")
    
    async def get_available_domains(self) -> List[str]:
        """Get list of all available domains."""
        try:
            redis = await self._get_redis()
            data = await redis.get("ha:metadata")
            if data:
                metadata = json.loads(data)
                return metadata.get("domains", [])
            return []
        except Exception as e:
            logger.error(f"Error getting available domains: {e}")
            return []
    
    async def get_state_summary(self) -> Dict[str, Any]:
        """Get summary statistics about cached state."""
        try:
            redis = await self._get_redis()
            data = await redis.get("ha:metadata")
            if data:
                metadata = json.loads(data)
                return {
                    "last_update": metadata.get("last_update"),
                    "total_entities": metadata.get("total_entities", 0),
                    "controllable_entities": metadata.get("controllable_entities", 0),
                    "available_domains": metadata.get("domains", []),
                    "domain_count": len(metadata.get("domains", []))
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting state summary: {e}")
            return {}
    
    async def is_cache_healthy(self) -> bool:
        """Check if the Redis cache has recent data."""
        try:
            summary = await self.get_state_summary()
            last_update = summary.get("last_update")
            
            if not last_update:
                return False
            
            # Check if data is less than 24 hours old (more realistic for cached data)  
            last_update_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            age_seconds = (datetime.utcnow() - last_update_dt.replace(tzinfo=None)).total_seconds()
            
            return age_seconds < 86400  # 24 hours
            
        except Exception as e:
            logger.error(f"Error checking cache health: {e}")
            return False
    
    async def get_entity_state_value(self, entity_id: str) -> Optional[str]:
        """Get just the state value for an entity."""
        entity = await self.get_entity(entity_id)
        if entity:
            return entity.get("state")
        return None
    
    async def get_entity_attributes(self, entity_id: str) -> Dict[str, Any]:
        """Get attributes for an entity."""
        entity = await self.get_entity(entity_id)
        if entity:
            return entity.get("attributes", {})
        return {}
    
    async def get_entity_friendly_name(self, entity_id: str) -> Optional[str]:
        """Get friendly name for an entity."""
        attributes = await self.get_entity_attributes(entity_id)
        return attributes.get("friendly_name")


# Global state manager instance
_state_manager = None

def get_ha_state_manager() -> HAStateManager:
    """Get the global state manager instance."""
    global _state_manager
    if not _state_manager:
        _state_manager = HAStateManager()
    return _state_manager


# Convenience functions for common operations
async def get_ha_entities() -> List[Dict[str, Any]]:
    """Get controllable entities (backward compatibility)."""
    manager = get_ha_state_manager()
    return await manager.get_controllable_entities()

async def get_ha_entity(entity_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific entity."""
    manager = get_ha_state_manager()
    return await manager.get_entity(entity_id)

async def get_ha_lights_on() -> List[Dict[str, Any]]:
    """Get all lights that are currently on."""
    manager = get_ha_state_manager()
    return await manager.get_lights_by_state("on")

async def get_ha_switches_on() -> List[Dict[str, Any]]:
    """Get all switches that are currently on."""
    manager = get_ha_state_manager()
    return await manager.get_switches_by_state("on")

async def get_ha_domain_entities(domain: str) -> List[Dict[str, Any]]:
    """Get all entities for a domain."""
    manager = get_ha_state_manager()
    return await manager.get_entities_by_domain(domain)

async def search_ha_entities(pattern: str) -> List[Dict[str, Any]]:
    """Search entities by pattern."""
    manager = get_ha_state_manager()
    return await manager.search_entities(pattern=pattern)