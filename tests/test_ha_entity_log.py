"""
Tests for Home Assistant Entity Logging functionality.
"""

import pytest
import json
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from mcp.ha_entity_log import (
    get_entity_log, 
    get_entity_log_summary, 
    get_all_logged_entities, 
    cleanup_old_logs
)


@pytest.mark.asyncio
class TestHAEntityLog:
    
    async def test_get_entity_log_empty(self):
        """Test getting log for entity with no entries."""
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zrevrangebyscore.return_value = []
            mock_get_redis.return_value = mock_redis
            
            log_entries = await get_entity_log("light.nonexistent")
            assert log_entries == []
            mock_redis.zrevrangebyscore.assert_called_once()

    async def test_get_entity_log_with_entries(self):
        """Test getting log entries for an entity."""
        entity_id = "light.test_log"
        
        # Create test log entries
        test_entries = []
        for i in range(3):
            timestamp = datetime.utcnow() - timedelta(minutes=i)
            entry = {
                "timestamp": timestamp.isoformat() + "Z",
                "entity_id": entity_id,
                "old_state": {"state": "off"},
                "new_state": {"state": "on"},
                "state_changed": True,
                "attributes_changed": False
            }
            test_entries.append(json.dumps(entry))
        
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zrevrangebyscore.return_value = test_entries
            mock_get_redis.return_value = mock_redis
            
            log_entries = await get_entity_log(entity_id, limit=10)
            
            assert len(log_entries) == 3
            assert log_entries[0]["entity_id"] == entity_id
            assert log_entries[0]["state_changed"] is True
            mock_redis.zrevrangebyscore.assert_called_once()

    async def test_get_entity_log_with_date_filter(self):
        """Test getting log entries with date filtering."""
        entity_id = "switch.test_log"
        
        # Create entries from different times
        now = datetime.utcnow()
        recent_entry = {
            "timestamp": (now - timedelta(hours=1)).isoformat() + "Z", 
            "entity_id": entity_id,
            "old_state": {"state": "on"},
            "new_state": {"state": "off"},
            "state_changed": True,
            "attributes_changed": False
        }
        
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zrevrangebyscore.return_value = [json.dumps(recent_entry)]
            mock_get_redis.return_value = mock_redis
            
            # Get entries from last 2 days only
            start_date = (now - timedelta(days=2)).isoformat() + "Z"
            log_entries = await get_entity_log(entity_id, start_date=start_date)
            
            assert len(log_entries) == 1
            assert log_entries[0]["timestamp"] == recent_entry["timestamp"]

    async def test_get_entity_log_summary(self):
        """Test getting entity log summary statistics."""
        entity_id = "climate.test_summary"
        
        # Create test entries with different change types
        now = datetime.utcnow()
        entries = [
            {
                "timestamp": (now - timedelta(hours=2)).isoformat() + "Z",
                "entity_id": entity_id,
                "state_changed": True,
                "attributes_changed": False
            },
            {
                "timestamp": (now - timedelta(hours=1)).isoformat() + "Z", 
                "entity_id": entity_id,
                "state_changed": False,
                "attributes_changed": True
            },
            {
                "timestamp": now.isoformat() + "Z",
                "entity_id": entity_id,
                "state_changed": True,
                "attributes_changed": True
            }
        ]
        
        with patch('mcp.ha_entity_log.get_entity_log') as mock_get_log:
            mock_get_log.return_value = entries
            
            summary = await get_entity_log_summary(entity_id, days=1)
            
            assert summary["entity_id"] == entity_id
            assert summary["total_changes"] == 3
            assert summary["state_changes"] == 2
            assert summary["attribute_changes"] == 2
            assert summary["change_frequency_per_day"] == 3.0
            assert summary["most_recent_change"] == entries[0]

    async def test_get_entity_log_summary_empty(self):
        """Test getting summary for entity with no logs."""
        entity_id = "sensor.empty"
        
        with patch('mcp.ha_entity_log.get_entity_log') as mock_get_log:
            mock_get_log.return_value = []
            
            summary = await get_entity_log_summary(entity_id, days=7)
            
            assert summary["entity_id"] == entity_id
            assert summary["total_changes"] == 0
            assert summary["state_changes"] == 0
            assert summary["attribute_changes"] == 0
            assert summary["most_recent_change"] is None
            assert summary["change_frequency_per_day"] == 0.0

    async def test_get_all_logged_entities(self):
        """Test getting list of all logged entities."""
        test_keys = [
            b"ha:log:light.test1",
            b"ha:log:switch.test2", 
            b"ha:log:climate.test3",
            b"ha:log:all"  # Should be filtered out
        ]
        
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.keys.return_value = test_keys
            mock_get_redis.return_value = mock_redis
            
            logged_entities = await get_all_logged_entities()
            
            expected_entities = ["climate.test3", "light.test1", "switch.test2"]
            assert logged_entities == expected_entities
            mock_redis.keys.assert_called_with("ha:log:*")

    async def test_cleanup_old_logs(self):
        """Test cleanup of old log entries."""
        test_keys = [b"ha:log:light.test", b"ha:log:switch.test"]
        
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.keys.return_value = test_keys
            mock_redis.zremrangebyscore.return_value = 5  # 5 entries removed per key
            mock_get_redis.return_value = mock_redis
            
            cleaned_count = await cleanup_old_logs(days_to_keep=7)
            
            assert cleaned_count == 10  # 5 * 2 keys
            assert mock_redis.zremrangebyscore.call_count == 2

    async def test_get_entity_log_invalid_json(self):
        """Test handling of invalid JSON in log entries."""
        entity_id = "light.bad_json"
        
        # Mix of valid and invalid JSON entries
        test_entries = [
            json.dumps({"timestamp": "2025-10-03T12:00:00Z", "entity_id": entity_id}),
            "invalid json string",
            json.dumps({"timestamp": "2025-10-03T11:00:00Z", "entity_id": entity_id})
        ]
        
        with patch('mcp.ha_entity_log.get_redis_client') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.zrevrangebyscore.return_value = test_entries
            mock_get_redis.return_value = mock_redis
            
            log_entries = await get_entity_log(entity_id)
            
            # Should only return valid JSON entries
            assert len(log_entries) == 2
            assert all("timestamp" in entry for entry in log_entries)


@pytest.mark.asyncio
class TestWebSocketLogging:
    
    async def test_log_state_change(self):
        """Test that WebSocket client logs state changes correctly."""
        from mcp.ha_websocket import HomeAssistantWebSocketClient
        
        client = HomeAssistantWebSocketClient()
        mock_redis = AsyncMock()
        client.redis_client = mock_redis
        
        entity_id = "light.test"
        old_state = {"state": "off", "attributes": {"brightness": None}}
        new_state = {"state": "on", "attributes": {"brightness": 255}}
        
        await client._log_state_change(entity_id, old_state, new_state)
        
        # Verify Redis operations were called
        mock_redis.zadd.assert_called()
        mock_redis.expire.assert_called()
        mock_redis.zremrangebyscore.assert_called()
        
        # Check that the log entry was properly formatted
        call_args = mock_redis.zadd.call_args_list[0]
        log_key = call_args[0][0]
        entry_data = call_args[0][1]
        
        assert log_key == f"ha:log:{entity_id}"
        assert len(entry_data) == 1  # One entry added
        
        # Parse the log entry
        entry_json = list(entry_data.keys())[0]
        entry = json.loads(entry_json)
        
        assert entry["entity_id"] == entity_id
        assert entry["old_state"] == old_state
        assert entry["new_state"] == new_state
        assert entry["state_changed"] is True
        assert entry["attributes_changed"] is True

    async def test_log_state_change_no_old_state(self):
        """Test logging when there's no old state (first time logging entity)."""
        from mcp.ha_websocket import HomeAssistantWebSocketClient
        
        client = HomeAssistantWebSocketClient()
        mock_redis = AsyncMock()
        client.redis_client = mock_redis
        
        entity_id = "sensor.new"
        old_state = None
        new_state = {"state": "online", "attributes": {"sensor_type": "temperature"}}
        
        await client._log_state_change(entity_id, old_state, new_state)
        
        # Verify Redis operations were called
        mock_redis.zadd.assert_called()
        
        # Check log entry content
        call_args = mock_redis.zadd.call_args_list[0]
        entry_json = list(call_args[0][1].keys())[0]
        entry = json.loads(entry_json)
        
        assert entry["old_state"] is None
        assert entry["new_state"] == new_state
        assert entry["state_changed"] is True  # Should be True when no old state
        assert entry["attributes_changed"] is True  # Should be True when no old state

    async def test_handle_state_change_calls_logging(self):
        """Test that _handle_state_change calls the logging method."""
        from mcp.ha_websocket import HomeAssistantWebSocketClient
        
        client = HomeAssistantWebSocketClient()
        mock_redis = AsyncMock()
        client.redis_client = mock_redis
        
        # Mock the logging method explicitly
        client._log_state_change = AsyncMock()
        
        # Mock the other methods called by _handle_state_change
        client._refresh_domain_cache = AsyncMock()
        client._refresh_controllable_cache = AsyncMock()
        
        # The event structure doesn't match what the method expects
        # Looking at the handler implementation, the data needs to be properly formatted
        event_data = {
            "event": {
                "data": {
                    "entity_id": "light.test",
                    "old_state": {"state": "off"},
                    "new_state": {"state": "on"}
                }
            }
        }
        
        await client._handle_state_change(event_data)
        
        # Verify that logging was called
        client._log_state_change.assert_called()
        
        # Verify other cache updates were called
        client._refresh_domain_cache.assert_called_with("light")
        client._refresh_controllable_cache.assert_called()


# Integration test fixtures
@pytest.fixture
async def mock_redis_with_logs():
    """Fixture that provides a mock Redis client with sample log data."""
    mock_redis = AsyncMock()
    
    # Sample log entries for different entities
    sample_logs = {
        "ha:log:light.living_room": [
            json.dumps({
                "timestamp": "2025-10-03T12:00:00Z",
                "entity_id": "light.living_room",
                "old_state": {"state": "off"},
                "new_state": {"state": "on"},
                "state_changed": True,
                "attributes_changed": False
            }),
            json.dumps({
                "timestamp": "2025-10-03T11:00:00Z",
                "entity_id": "light.living_room", 
                "old_state": {"state": "on"},
                "new_state": {"state": "off"},
                "state_changed": True,
                "attributes_changed": False
            })
        ]
    }
    
    def mock_zrevrangebyscore(key, max_score, min_score, start=0, num=100):
        return sample_logs.get(key, [])
    
    mock_redis.zrevrangebyscore.side_effect = mock_zrevrangebyscore
    mock_redis.keys.return_value = list(sample_logs.keys())
    
    return mock_redis