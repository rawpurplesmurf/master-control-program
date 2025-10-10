"""
Tests for the WebSocket-based Home Assistant integration.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from mcp.ha_websocket import HomeAssistantWebSocketClient
from mcp.ha_state import HAStateManager, get_ha_state_manager


@pytest.mark.asyncio
class TestHAWebSocketClient:
    
    async def test_websocket_client_initialization(self):
        """Test WebSocket client can be initialized."""
        client = HomeAssistantWebSocketClient()
        assert client.websocket is None
        assert client.is_authenticated is False
        assert client.is_running is False
        assert client.message_id == 1
    
    async def test_message_id_increment(self):
        """Test message ID increments correctly."""
        client = HomeAssistantWebSocketClient()
        assert client._next_message_id() == 1
        assert client._next_message_id() == 2
        assert client._next_message_id() == 3
    
    @patch('mcp.ha_websocket.websockets.connect', new_callable=AsyncMock)
    @patch('mcp.ha_websocket.get_redis_client')
    async def test_connect_success(self, mock_get_redis, mock_websockets):
        """Test successful WebSocket connection."""
        mock_websocket = AsyncMock()
        mock_websockets.return_value = mock_websocket
        # Mock Redis client
        mock_redis_client = AsyncMock()
        mock_get_redis.return_value = mock_redis_client
        
        client = HomeAssistantWebSocketClient()
        result = await client.connect()
        
        assert result is True
        assert client.websocket == mock_websocket
        assert client.redis_client == mock_redis_client
        mock_websockets.assert_called_once()
        mock_get_redis.assert_called_once()
    
    @patch('mcp.ha_websocket.websockets.connect')
    @patch('mcp.ha_websocket.get_redis_client')
    async def test_connect_failure(self, mock_get_redis, mock_websockets):
        """Test WebSocket connection failure."""
        mock_redis_client = AsyncMock()
        mock_get_redis.return_value = mock_redis_client
        mock_websockets.side_effect = Exception("Connection failed")
        
        client = HomeAssistantWebSocketClient()
        result = await client.connect()
        
        assert result is False
        assert client.websocket is None
    
    @patch('mcp.ha_websocket.get_redis_client')
    async def test_connect_redis_failure(self, mock_get_redis):
        """Test WebSocket connection fails when Redis client is unavailable."""
        mock_get_redis.return_value = None  # Redis client initialization fails
        
        client = HomeAssistantWebSocketClient()
        result = await client.connect()
        
        assert result is False
        assert client.redis_client is None
        mock_get_redis.assert_called_once()
    
    async def test_cache_states(self):
        """Test state caching functionality."""
        client = HomeAssistantWebSocketClient()
        mock_redis = AsyncMock()
        client.redis_client = mock_redis
        
        test_states = [
            {
                "entity_id": "light.living_room",
                "state": "on",
                "attributes": {"friendly_name": "Living Room Light"}
            },
            {
                "entity_id": "switch.kitchen",
                "state": "off", 
                "attributes": {"friendly_name": "Kitchen Switch"}
            }
        ]
        
        await client._cache_states(test_states)
        
        # Verify Redis calls were made
        assert mock_redis.setex.call_count >= 3  # all_states, entities, metadata
    
    async def test_handle_state_change(self):
        """Test state change event handling."""
        client = HomeAssistantWebSocketClient()
        mock_redis = AsyncMock()
        client.redis_client = mock_redis
        
        # Updated to match the correct nested structure from WebSocket events
        event_data = {
            "event": {
                "data": {
                    "entity_id": "light.living_room",
                    "old_state": {
                        "entity_id": "light.living_room",
                        "state": "on",
                        "attributes": {"friendly_name": "Living Room Light"}
                    },
                    "new_state": {
                        "entity_id": "light.living_room", 
                        "state": "off",
                        "attributes": {"friendly_name": "Living Room Light"}
                    }
                }
            }
        }
        
        with patch.object(client, '_refresh_domain_cache') as mock_refresh_domain:
            with patch.object(client, '_refresh_controllable_cache') as mock_refresh_controllable:
                with patch.object(client, '_log_state_change') as mock_log_state:
                    await client._handle_state_change(event_data)
                    
                    # Should update individual entity cache
                    mock_redis.setex.assert_called()
                    # Should log state change
                    mock_log_state.assert_called_once()
                    # Should refresh domain cache
                    mock_refresh_domain.assert_called_with("light")
                    # Should refresh controllable cache since light is controllable
                    mock_refresh_controllable.assert_called()


@pytest.mark.asyncio 
class TestHAStateManager:
    
    async def test_state_manager_initialization(self):
        """Test state manager can be initialized."""
        manager = HAStateManager()
        assert manager.redis_client is None
    
    async def test_get_global_state_manager(self):
        """Test global state manager instance."""
        manager1 = get_ha_state_manager()
        manager2 = get_ha_state_manager()
        assert manager1 is manager2  # Should be same instance
    
    async def test_get_all_entities(self):
        """Test getting all entities from cache."""
        manager = HAStateManager()
        
        # Mock the _get_redis method directly
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([
            {"entity_id": "light.test", "state": "on"}
        ])
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        entities = await manager.get_all_entities()
        
        assert len(entities) == 1
        assert entities[0]["entity_id"] == "light.test"
        mock_redis.get.assert_called_with("ha:all_states")
    
    async def test_get_controllable_entities(self):
        """Test getting controllable entities (backward compatibility).""" 
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([
            {"entity_id": "light.test", "state": "on"},
            {"entity_id": "switch.test", "state": "off"}
        ])
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        entities = await manager.get_controllable_entities()
        
        assert len(entities) == 2
        mock_redis.get.assert_called_with("ha:entities")
    
    async def test_get_specific_entity(self):
        """Test getting a specific entity by ID."""
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({
            "entity_id": "light.living_room", 
            "state": "on",
            "attributes": {"friendly_name": "Living Room"}
        })
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        entity = await manager.get_entity("light.living_room")
        
        assert entity["entity_id"] == "light.living_room"
        assert entity["state"] == "on"
        mock_redis.get.assert_called_with("ha:entity:light.living_room")
    
    async def test_get_entities_by_domain(self):
        """Test getting entities by domain."""
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([
            {"entity_id": "light.living_room", "state": "on"},
            {"entity_id": "light.bedroom", "state": "off"}
        ])
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        entities = await manager.get_entities_by_domain("light")
        
        assert len(entities) == 2
        assert all("light." in e["entity_id"] for e in entities)
        mock_redis.get.assert_called_with("ha:domain:light")
    
    async def test_search_entities_by_pattern(self):
        """Test searching entities by pattern."""
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([
            {"entity_id": "light.living_room", "state": "on"},
            {"entity_id": "light.bedroom", "state": "off"},
            {"entity_id": "switch.kitchen", "state": "on"}
        ])
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        entities = await manager.search_entities(pattern="living")
        
        # Should find only entities with "living" in the ID
        assert len(entities) == 1
        assert entities[0]["entity_id"] == "light.living_room"
    
    async def test_get_lights_by_state(self):
        """Test getting lights by state."""
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps([
            {"entity_id": "light.living_room", "state": "on"},
            {"entity_id": "light.bedroom", "state": "off"}
        ])
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        on_lights = await manager.get_lights_by_state("on")
        
        assert len(on_lights) == 1
        assert on_lights[0]["state"] == "on"
    
    async def test_cache_health_check(self):
        """Test cache health checking."""
        from datetime import datetime
        
        manager = HAStateManager()
        
        mock_redis = AsyncMock()
        # Mock recent update (should be healthy)
        recent_time = datetime.utcnow().isoformat()
        mock_redis.get.return_value = json.dumps({
            "last_update": recent_time,
            "total_entities": 100
        })
        manager._get_redis = AsyncMock(return_value=mock_redis)
        
        is_healthy = await manager.is_cache_healthy()
        
        assert is_healthy is True


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions."""
    with patch('mcp.ha_state.get_ha_state_manager') as mock_get_manager:
        mock_manager = AsyncMock()
        mock_manager.get_controllable_entities.return_value = [
            {"entity_id": "light.test", "state": "on"}
        ]
        mock_get_manager.return_value = mock_manager
        
        from mcp.ha_state import get_ha_entities
        entities = await get_ha_entities()
        
        assert len(entities) == 1
        mock_manager.get_controllable_entities.assert_called_once()