"""
Home Assistant Services Manager
Provides functions to discover and manage HA services with Redis caching.
"""
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from datetime import datetime

from mcp.config import settings
from mcp.cache import get_redis_client

logger = logging.getLogger(__name__)

class HomeAssistantServicesManager:
    """Manages Home Assistant service discovery and caching."""
    
    def __init__(self):
        self.base_url = settings.HA_URL.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {settings.HA_TOKEN}",
            "Content-Type": "application/json"
        }
        self.redis_client = None
    
    async def _get_redis_client(self):
        """Get Redis client for service caching."""
        if not self.redis_client:
            self.redis_client = get_redis_client()
        return self.redis_client
    
    async def get_available_services(self, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get all available Home Assistant services.
        
        Args:
            use_cache: Whether to use cached data (default: True)
            
        Returns:
            Dictionary of services organized by domain
        """
        try:
            redis_client = await self._get_redis_client()
            cache_key = "ha:services:all"
            
            # Try cache first if enabled
            if use_cache:
                cached_services = await redis_client.get(cache_key)
                if cached_services:
                    try:
                        services_data = json.loads(cached_services)
                        logger.debug("📦 Using cached HA services data")
                        return services_data
                    except json.JSONDecodeError:
                        logger.warning("Invalid cached services data, fetching fresh")
            
            # Fetch fresh data from Home Assistant
            logger.info("🔄 Fetching HA services from /api/services")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/api/services",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    logger.error(f"HA services API returned {response.status_code}: {response.text}")
                    return self._get_fallback_services()
                
                raw_services = response.json()
                
                # Transform HA services format to our organized format
                organized_services = await self._organize_services(raw_services)
                
                # Cache the result (5 minute TTL - services don't change often)
                await redis_client.setex(
                    cache_key, 
                    300,  # 5 minutes
                    json.dumps(organized_services)
                )
                
                logger.info(f"✅ Fetched and cached {len(organized_services['services'])} service domains")
                return organized_services
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching HA services")
            return self._get_fallback_services()
        except Exception as e:
            logger.error(f"Error fetching HA services: {e}")
            return self._get_fallback_services()
    
    async def _organize_services(self, raw_services: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Transform HA's raw services format into organized structure.
        
        Args:
            raw_services: Raw services list from HA /api/services
            
        Returns:
            Organized services dictionary
        """
        organized = {
            "services": {},
            "total_services": 0,
            "total_domains": 0,
            "last_updated": None
        }
        
        try:
            for domain_data in raw_services:
                domain = domain_data.get("domain")
                if not domain:
                    continue
                
                domain_services = []
                services = domain_data.get("services", {})
                
                for service_name, service_info in services.items():
                    service_entry = {
                        "service": f"{domain}.{service_name}",
                        "name": service_name,
                        "description": service_info.get("description", ""),
                        "fields": []
                    }
                    
                    # Extract service parameters/fields
                    fields = service_info.get("fields", {})
                    for field_name, field_info in fields.items():
                        field_entry = {
                            "name": field_name,
                            "description": field_info.get("description", ""),
                            "required": field_info.get("required", False),
                            "selector": field_info.get("selector", {}),
                            "example": field_info.get("example")
                        }
                        service_entry["fields"].append(field_entry)
                    
                    # Legacy parameters list for backward compatibility
                    service_entry["parameters"] = [f["name"] for f in service_entry["fields"]]
                    
                    domain_services.append(service_entry)
                    organized["total_services"] += 1
                
                if domain_services:
                    organized["services"][domain] = domain_services
                    organized["total_domains"] += 1
            
            # Add timestamp
            organized["last_updated"] = datetime.utcnow().isoformat() + "Z"
            
            return organized
            
        except Exception as e:
            logger.error(f"Error organizing services: {e}")
            return self._get_fallback_services()
    
    def _get_fallback_services(self) -> Dict[str, Any]:
        """
        Return fallback services if HA API is unavailable.
        
        Returns:
            Basic service mappings for common domains
        """
        logger.warning("🔄 Using fallback services - HA API unavailable")
        
        return {
            "services": {
                "light": [
                    {
                        "service": "light.turn_on",
                        "name": "turn_on", 
                        "description": "Turn the light on",
                        "parameters": ["brightness", "color_name", "rgb_color", "effect"],
                        "fields": [
                            {"name": "brightness", "description": "Brightness level (0-255)", "required": False},
                            {"name": "color_name", "description": "Color name", "required": False},
                            {"name": "rgb_color", "description": "RGB color tuple", "required": False},
                            {"name": "effect", "description": "Light effect", "required": False}
                        ]
                    },
                    {
                        "service": "light.turn_off",
                        "name": "turn_off",
                        "description": "Turn the light off", 
                        "parameters": [],
                        "fields": []
                    },
                    {
                        "service": "light.toggle",
                        "name": "toggle",
                        "description": "Toggle the light",
                        "parameters": [],
                        "fields": []
                    }
                ],
                "switch": [
                    {
                        "service": "switch.turn_on",
                        "name": "turn_on",
                        "description": "Turn the switch on",
                        "parameters": [],
                        "fields": []
                    },
                    {
                        "service": "switch.turn_off", 
                        "name": "turn_off",
                        "description": "Turn the switch off",
                        "parameters": [],
                        "fields": []
                    },
                    {
                        "service": "switch.toggle",
                        "name": "toggle", 
                        "description": "Toggle the switch",
                        "parameters": [],
                        "fields": []
                    }
                ],
                "homeassistant": [
                    {
                        "service": "homeassistant.turn_on",
                        "name": "turn_on",
                        "description": "Generic turn on",
                        "parameters": [],
                        "fields": []
                    },
                    {
                        "service": "homeassistant.turn_off",
                        "name": "turn_off", 
                        "description": "Generic turn off",
                        "parameters": [],
                        "fields": []
                    },
                    {
                        "service": "homeassistant.toggle",
                        "name": "toggle",
                        "description": "Generic toggle", 
                        "parameters": [],
                        "fields": []
                    }
                ]
            },
            "total_services": 9,
            "total_domains": 3,
            "last_updated": None,
            "fallback": True
        }
    
    async def get_services_for_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get services available for a specific domain.
        
        Args:
            domain: The domain to get services for (e.g., 'light', 'switch')
            
        Returns:
            List of services for the domain
        """
        try:
            all_services = await self.get_available_services()
            return all_services.get("services", {}).get(domain, [])
            
        except Exception as e:
            logger.error(f"Error getting services for domain {domain}: {e}")
            return []
    
    async def validate_service(self, service: str) -> Dict[str, Any]:
        """
        Validate if a service exists and get its information.
        
        Args:
            service: Service name in format 'domain.service'
            
        Returns:
            Validation result with service info
        """
        try:
            if '.' not in service:
                return {
                    "valid": False,
                    "error": f"Invalid service format: {service}. Expected 'domain.service'"
                }
            
            domain, service_name = service.split('.', 1)
            domain_services = await self.get_services_for_domain(domain)
            
            # Find the service
            service_info = None
            for svc in domain_services:
                if svc.get("service") == service or svc.get("name") == service_name:
                    service_info = svc
                    break
            
            if service_info:
                return {
                    "valid": True,
                    "service_info": service_info,
                    "domain": domain
                }
            else:
                return {
                    "valid": False,
                    "error": f"Service {service} not found in domain {domain}",
                    "available_services": [s.get("service") for s in domain_services]
                }
                
        except Exception as e:
            logger.error(f"Error validating service {service}: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    async def refresh_services_cache(self) -> Dict[str, Any]:
        """
        Force refresh of services cache.
        
        Returns:
            Fresh services data
        """
        return await self.get_available_services(use_cache=False)

# Global services manager instance
_services_manager = HomeAssistantServicesManager()

async def get_ha_services(use_cache: bool = True) -> Dict[str, Any]:
    """Get all available Home Assistant services."""
    return await _services_manager.get_available_services(use_cache)

async def get_ha_services_for_domain(domain: str) -> List[Dict[str, Any]]:
    """Get services for a specific domain."""
    return await _services_manager.get_services_for_domain(domain)

async def validate_ha_service(service: str) -> Dict[str, Any]:
    """Validate a Home Assistant service."""
    return await _services_manager.validate_service(service)

async def refresh_ha_services_cache() -> Dict[str, Any]:
    """Force refresh of HA services cache."""
    return await _services_manager.refresh_services_cache()