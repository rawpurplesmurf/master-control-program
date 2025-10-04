import json
import pytest
from unittest.mock import patch, MagicMock

import homeassistant.poller as poller

@patch('homeassistant.poller.requests.get')
@patch('homeassistant.poller.redis.Redis')
def test_poll_and_cache_entities(mock_redis_cls, mock_requests_get):
    # Mock Home Assistant API response
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"entity_id": "light.living_room", "state": "on"},
        {"entity_id": "sensor.temperature", "state": "22"},
        {"entity_id": "switch.kitchen", "state": "off"},
    ]
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response

    # Mock Redis
    mock_redis = MagicMock()
    mock_redis_cls.from_url.return_value = mock_redis

    poller.poll_and_cache_entities()

    # Only controllable entities should be cached
    cached = json.loads(mock_redis.set.call_args[0][1])
    entity_ids = {e["entity_id"] for e in cached}
    assert "light.living_room" in entity_ids
    assert "switch.kitchen" in entity_ids
    assert "sensor.temperature" not in entity_ids
    mock_redis.set.assert_called_once_with("ha:entities", mock_redis.set.call_args[0][1])
