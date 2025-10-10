"""
Tests for Home Assistant Services Manager
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from mcp.ha_services import (
    HomeAssistantServicesManager,
    get_ha_services,
    get_ha_services_for_domain,
    validate_ha_service,
    refresh_ha_services_cache
)

@pytest.fixture
def services_manager():
    """Create services manager instance for testing."""
    return HomeAssistantServicesManager()

@pytest.fixture
def mock_ha_services_response():
    """Mock HA services API response."""
    return [
        {
            "domain": "light",
            "services": {
                "turn_on": {
                    "description": "Turn the light on",
                    "fields": {
                        "brightness": {
                            "description": "Brightness level",
                            "required": False,
                            "selector": {"number": {"min": 0, "max": 255}}
                        },
                        "color_name": {
                            "description": "Color name",
                            "required": False,
                            "example": "red"
                        }
                    }
                },
                "turn_off": {
                    "description": "Turn the light off",
                    "fields": {}
                }
            }
        },
        {
            "domain": "switch", 
            "services": {
                "turn_on": {
                    "description": "Turn the switch on",
                    "fields": {}
                },
                "turn_off": {
                    "description": "Turn the switch off", 
                    "fields": {}
                }
            }
        }
    ]

@pytest.mark.asyncio
async def test_get_services_from_ha_api(services_manager, mock_ha_services_response):
    """Test fetching services from HA API."""
    # Mock Redis client
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_ha_services_response
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        result = await services_manager.get_available_services(use_cache=False)
        
        assert result.get("fallback") is not True  # Should not have fallback flag
        assert "light" in result["services"]
        assert "switch" in result["services"]
        assert result["total_domains"] == 2
        assert result["total_services"] == 4  # 2 light + 2 switch services
        
        # Check service structure
        light_services = result["services"]["light"]
        assert len(light_services) == 2
        
        turn_on_service = next(s for s in light_services if s["name"] == "turn_on")
        assert turn_on_service["service"] == "light.turn_on"
        assert turn_on_service["description"] == "Turn the light on"
        assert len(turn_on_service["fields"]) == 2
        assert "brightness" in turn_on_service["parameters"]
        assert "color_name" in turn_on_service["parameters"]

@pytest.mark.asyncio
async def test_get_services_with_cache(services_manager):
    """Test using cached services data."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Set up cached data
    cached_data = {
        "services": {"test": [{"service": "test.service"}]},
        "total_services": 1,
        "total_domains": 1
    }
    mock_redis.get.return_value = json.dumps(cached_data)
    
    result = await services_manager.get_available_services(use_cache=True)
    
    assert result == cached_data

@pytest.mark.asyncio
async def test_get_services_fallback_on_error(services_manager):
    """Test fallback services when HA API fails."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    mock_redis.get.return_value = None
    
    # Mock HTTP error
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.RequestError("Connection failed")
        
        result = await services_manager.get_available_services(use_cache=False)
        
        assert result.get("fallback") is True
        assert "light" in result["services"]
        assert "switch" in result["services"]
        assert "homeassistant" in result["services"]

@pytest.mark.asyncio
async def test_get_services_for_domain(services_manager):
    """Test getting services for specific domain."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Mock cached services
    cached_data = {
        "services": {
            "light": [
                {"service": "light.turn_on", "name": "turn_on"},
                {"service": "light.turn_off", "name": "turn_off"}
            ],
            "switch": [
                {"service": "switch.turn_on", "name": "turn_on"}
            ]
        }
    }
    mock_redis.get.return_value = json.dumps(cached_data)
    
    light_services = await services_manager.get_services_for_domain("light")
    
    assert len(light_services) == 2
    assert light_services[0]["service"] == "light.turn_on"
    assert light_services[1]["service"] == "light.turn_off"

@pytest.mark.asyncio
async def test_validate_service_valid(services_manager):
    """Test validating a valid service."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Mock cached services
    cached_data = {
        "services": {
            "light": [
                {
                    "service": "light.turn_on",
                    "name": "turn_on",
                    "description": "Turn light on"
                }
            ]
        }
    }
    mock_redis.get.return_value = json.dumps(cached_data)
    
    result = await services_manager.validate_service("light.turn_on")
    
    assert result["valid"] is True
    assert result["service_info"]["service"] == "light.turn_on"
    assert result["domain"] == "light"

@pytest.mark.asyncio
async def test_validate_service_invalid_format(services_manager):
    """Test validating service with invalid format."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    result = await services_manager.validate_service("invalid_service")
    
    assert result["valid"] is False
    assert "Invalid service format" in result["error"]

@pytest.mark.asyncio
async def test_validate_service_not_found(services_manager):
    """Test validating non-existent service."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Mock empty services
    cached_data = {"services": {"light": []}}
    mock_redis.get.return_value = json.dumps(cached_data)
    
    result = await services_manager.validate_service("light.nonexistent")
    
    assert result["valid"] is False
    assert "not found" in result["error"]
    assert "available_services" in result

@pytest.mark.asyncio
async def test_refresh_services_cache():
    """Test force refreshing services cache."""
    with patch('mcp.ha_services._services_manager.get_available_services') as mock_get:
        mock_get.return_value = {"services": {"test": []}}
        
        result = await refresh_ha_services_cache()
        
        mock_get.assert_called_once_with(use_cache=False)
        assert result == {"services": {"test": []}}

@pytest.mark.asyncio
async def test_module_level_functions():
    """Test module-level convenience functions."""
    with patch('mcp.ha_services._services_manager') as mock_manager:
        # Mock async methods properly
        mock_manager.get_available_services = AsyncMock(return_value={"test": "data"})
        mock_manager.get_services_for_domain = AsyncMock(return_value=["service1"])
        mock_manager.validate_service = AsyncMock(return_value={"valid": True})
        
        # Test get_ha_services
        result = await get_ha_services()
        mock_manager.get_available_services.assert_called_once_with(True)
        assert result == {"test": "data"}
        
        # Test get_ha_services_for_domain
        result = await get_ha_services_for_domain("light")
        mock_manager.get_services_for_domain.assert_called_once_with("light")
        assert result == ["service1"]
        
        # Test validate_ha_service
        result = await validate_ha_service("light.turn_on")
        mock_manager.validate_service.assert_called_once_with("light.turn_on")
        assert result == {"valid": True}

@pytest.mark.asyncio
async def test_organize_services_structure(services_manager):
    """Test the service organization logic."""
    raw_services = [
        {
            "domain": "test_domain",
            "services": {
                "test_service": {
                    "description": "Test service description",
                    "fields": {
                        "param1": {
                            "description": "Parameter 1",
                            "required": True,
                            "example": "example_value"
                        },
                        "param2": {
                            "description": "Parameter 2", 
                            "required": False
                        }
                    }
                }
            }
        }
    ]
    
    result = await services_manager._organize_services(raw_services)
    
    assert result["total_domains"] == 1
    assert result["total_services"] == 1
    assert "last_updated" in result
    
    service = result["services"]["test_domain"][0]
    assert service["service"] == "test_domain.test_service"
    assert service["name"] == "test_service"
    assert service["description"] == "Test service description"
    assert len(service["fields"]) == 2
    assert len(service["parameters"]) == 2
    
    # Check field structure
    field1 = next(f for f in service["fields"] if f["name"] == "param1")
    assert field1["required"] is True
    assert field1["example"] == "example_value"
    
    field2 = next(f for f in service["fields"] if f["name"] == "param2")
    assert field2["required"] is False

@pytest.mark.asyncio
async def test_http_timeout_handling(services_manager):
    """Test handling of HTTP timeouts."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    mock_redis.get.return_value = None
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.TimeoutException("Timeout")
        
        result = await services_manager.get_available_services(use_cache=False)
        
        assert result.get("fallback") is True
        assert "services" in result

@pytest.mark.asyncio
async def test_invalid_cached_data(services_manager):
    """Test handling of invalid cached JSON data."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    
    # Set invalid JSON in cache
    mock_redis.get.return_value = "invalid json data"
    
    # Mock successful HTTP response with proper service structure
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "domain": "test", 
            "services": {
                "test_service": {
                    "description": "Test service",
                    "fields": {}
                }
            }
        }
    ]
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        result = await services_manager.get_available_services(use_cache=True)
        
        # Should fetch fresh data due to invalid cache
        assert "test" in result["services"]
        assert len(result["services"]["test"]) == 1
        assert result["services"]["test"][0]["service"] == "test.test_service"

@pytest.mark.asyncio
async def test_empty_services_response(services_manager):
    """Test handling empty services response from HA."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    mock_redis.get.return_value = None
    
    # Mock empty HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        result = await services_manager.get_available_services(use_cache=False)
        
        assert result["total_services"] == 0
        assert result["total_domains"] == 0
        assert result["services"] == {}

@pytest.mark.asyncio
async def test_http_error_status_codes(services_manager):
    """Test handling of various HTTP error status codes."""
    mock_redis = AsyncMock()
    services_manager.redis_client = mock_redis
    mock_redis.get.return_value = None
    
    # Mock HTTP 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        result = await services_manager.get_available_services(use_cache=False)
        
        assert result.get("fallback") is True