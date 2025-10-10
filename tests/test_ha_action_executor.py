"""
Tests for Home Assistant Action Executor
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from datetime import datetime

from mcp.ha_action_executor import (
    HomeAssistantActionExecutor,
    execute_ha_action,
    get_ha_action_history
)

@pytest.fixture
def action_executor():
    """Create action executor instance for testing."""
    return HomeAssistantActionExecutor()

@pytest.fixture
def valid_action():
    """Valid test action."""
    return {
        "service": "light.turn_on",
        "entity_id": "light.living_room",
        "data": {
            "brightness": 255
        }
    }

@pytest.fixture
def mock_entity():
    """Mock HA entity."""
    return {
        "entity_id": "light.living_room",
        "state": "off",
        "attributes": {
            "friendly_name": "Living Room Light",
            "brightness": 128
        }
    }

@pytest.fixture
def mock_controllable_entities():
    """Mock controllable entities."""
    return [
        {
            "entity_id": "light.living_room",
            "state": "off"
        },
        {
            "entity_id": "switch.outlet",
            "state": "on"
        }
    ]

@pytest.mark.asyncio
async def test_execute_action_success(action_executor, valid_action, mock_entity, mock_controllable_entities):
    """Test successful action execution."""
    # Mock Redis client
    mock_redis = AsyncMock()
    action_executor.redis_client = mock_redis
    
    # Mock service validation
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {
            "valid": True,
            "service_info": {
                "service": "light.turn_on",
                "description": "Turn on light"
            }
        }
        
        # Mock entity validation
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = mock_entity
            
            with patch('mcp.ha_action_executor.get_ha_entities') as mock_get_controllable:
                mock_get_controllable.return_value = mock_controllable_entities
                
                # Mock HA service call
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                    
                    result = await action_executor.execute_action(valid_action)
                    
                    assert result["success"] is True
                    assert result["service"] == "light.turn_on"
                    assert result["entity_id"] == "light.living_room"
                    assert "timestamp" in result
                    
                    # Verify Redis logging was called
                    mock_redis.zadd.assert_called()

@pytest.mark.asyncio
async def test_execute_action_invalid_format(action_executor):
    """Test action with invalid format."""
    invalid_action = {"invalid": "action"}
    
    result = await action_executor.execute_action(invalid_action)
    
    assert result["success"] is False
    assert "Invalid action format" in result["error"]

@pytest.mark.asyncio
async def test_execute_action_invalid_service(action_executor, valid_action):
    """Test action with invalid service."""
    # Mock service validation failure
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {
            "valid": False,
            "error": "Service not found",
            "available_services": ["light.turn_on", "light.turn_off"]
        }
        
        result = await action_executor.execute_action(valid_action)
        
        assert result["success"] is False
        assert "Service not found" in result["error"]
        assert "available_services" in result

@pytest.mark.asyncio
async def test_execute_action_entity_not_found(action_executor, valid_action):
    """Test action with non-existent entity."""
    # Mock service validation success
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock entity not found
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = None
            
            result = await action_executor.execute_action(valid_action)
            
            assert result["success"] is False
            assert "not found" in result["error"]

@pytest.mark.asyncio
async def test_execute_action_entity_not_controllable(action_executor, valid_action, mock_entity):
    """Test action with non-controllable entity."""
    # Mock service validation success
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock entity exists
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = mock_entity
            
            # Mock entity not in controllable list
            with patch('mcp.ha_action_executor.get_ha_entities') as mock_get_controllable:
                mock_get_controllable.return_value = []
                
                result = await action_executor.execute_action(valid_action)
                
                assert result["success"] is False
                assert "not controllable" in result["error"]

@pytest.mark.asyncio
async def test_execute_action_ha_service_failure(action_executor, valid_action, mock_entity, mock_controllable_entities):
    """Test HA service call failure."""
    # Mock Redis client
    mock_redis = AsyncMock()
    action_executor.redis_client = mock_redis
    
    # Mock service validation
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock entity validation
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = mock_entity
            
            with patch('mcp.ha_action_executor.get_ha_entities') as mock_get_controllable:
                mock_get_controllable.return_value = mock_controllable_entities
                
                # Mock HA service call failure
                mock_response = MagicMock()
                mock_response.status_code = 400
                mock_response.text = "Bad Request"
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                    
                    result = await action_executor.execute_action(valid_action)
                    
                    assert result["success"] is False
                    assert "Home Assistant service call failed" in result["error"]

@pytest.mark.asyncio
async def test_execute_action_without_entity_id(action_executor):
    """Test action without entity_id (service-only call)."""
    action_without_entity = {
        "service": "homeassistant.restart"
    }
    
    # Mock Redis client
    mock_redis = AsyncMock()
    action_executor.redis_client = mock_redis
    
    # Mock service validation
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock HA service call
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await action_executor.execute_action(action_without_entity)
            
            assert result["success"] is True
            assert result["entity_id"] is None

@pytest.mark.asyncio
async def test_validate_action_method(action_executor):
    """Test action validation method."""
    # Valid action
    valid = action_executor._validate_action({
        "service": "light.turn_on",
        "entity_id": "light.test"
    })
    assert valid is True
    
    # Invalid - not dict
    invalid1 = action_executor._validate_action("not a dict")
    assert invalid1 is False
    
    # Invalid - no service
    invalid2 = action_executor._validate_action({
        "entity_id": "light.test"
    })
    assert invalid2 is False
    
    # Invalid - service without dot
    invalid3 = action_executor._validate_action({
        "service": "invalid_service"
    })
    assert invalid3 is False

@pytest.mark.asyncio
async def test_get_action_history(action_executor):
    """Test getting action history for an entity."""
    mock_redis = AsyncMock()
    action_executor.redis_client = mock_redis
    
    # Mock Redis response
    log_entries = [
        json.dumps({
            "timestamp": "2023-01-01T12:00:00Z",
            "action": {"service": "light.turn_on"},
            "success": True
        }),
        json.dumps({
            "timestamp": "2023-01-01T11:00:00Z",
            "action": {"service": "light.turn_off"},
            "success": True
        })
    ]
    mock_redis.zrevrange.return_value = log_entries
    
    history = await action_executor.get_action_history("light.living_room", 10)
    
    assert len(history) == 2
    assert history[0]["action"]["service"] == "light.turn_on"
    assert history[1]["action"]["service"] == "light.turn_off"
    
    # Verify Redis call
    mock_redis.zrevrange.assert_called_once_with("ha:actions:light.living_room", 0, 9)

@pytest.mark.asyncio
async def test_get_action_history_invalid_json(action_executor):
    """Test handling invalid JSON in action history."""
    mock_redis = AsyncMock()
    action_executor.redis_client = mock_redis
    
    # Mock Redis response with invalid JSON
    log_entries = [
        "invalid json",
        json.dumps({"valid": "entry"})
    ]
    mock_redis.zrevrange.return_value = log_entries
    
    history = await action_executor.get_action_history("light.living_room", 10)
    
    # Should skip invalid JSON and return only valid entries
    assert len(history) == 1
    assert history[0]["valid"] == "entry"

@pytest.mark.asyncio
async def test_module_level_functions():
    """Test module-level convenience functions."""
    test_action = {"service": "light.turn_on"}
    
    with patch('mcp.ha_action_executor._action_executor') as mock_executor:
        # Mock async methods properly
        mock_executor.execute_action = AsyncMock(return_value={"success": True})
        mock_executor.get_action_history = AsyncMock(return_value=[{"action": "test"}])
        
        # Test execute_ha_action
        result = await execute_ha_action(test_action)
        mock_executor.execute_action.assert_called_once_with(test_action)
        assert result == {"success": True}
        
        # Test get_ha_action_history
        result = await get_ha_action_history("light.test", 25)
        mock_executor.get_action_history.assert_called_once_with("light.test", 25)
        assert result == [{"action": "test"}]

@pytest.mark.asyncio
async def test_http_timeout_handling(action_executor, valid_action, mock_entity, mock_controllable_entities):
    """Test HTTP timeout handling."""
    # Mock service validation
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock entity validation
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = mock_entity
            
            with patch('mcp.ha_action_executor.get_ha_entities') as mock_get_controllable:
                mock_get_controllable.return_value = mock_controllable_entities
                
                # Mock HTTP timeout
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.TimeoutException("Timeout")
                    
                    result = await action_executor.execute_action(valid_action)
                    
                    assert result["success"] is False
                    assert "timed out" in result["error"]

@pytest.mark.asyncio
async def test_action_logging_redis_error(action_executor, valid_action, mock_entity, mock_controllable_entities):
    """Test handling Redis errors during action logging."""
    # Mock Redis client with error
    mock_redis = AsyncMock()
    mock_redis.zadd.side_effect = Exception("Redis error")
    action_executor.redis_client = mock_redis
    
    # Mock service validation
    with patch('mcp.ha_action_executor.validate_ha_service') as mock_validate:
        mock_validate.return_value = {"valid": True}
        
        # Mock entity validation
        with patch('mcp.ha_action_executor.get_ha_entity') as mock_get_entity:
            mock_get_entity.return_value = mock_entity
            
            with patch('mcp.ha_action_executor.get_ha_entities') as mock_get_controllable:
                mock_get_controllable.return_value = mock_controllable_entities
                
                # Mock HA service call success
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = []
                
                with patch('httpx.AsyncClient') as mock_client:
                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                    
                    # Should still succeed even if logging fails
                    result = await action_executor.execute_action(valid_action)
                    
                    assert result["success"] is True
                    # Redis error should be logged but not fail the action