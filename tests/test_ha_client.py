import pytest
from unittest.mock import patch, MagicMock
import homeassistant.ha_client as ha_client

def test_call_service_success():
    with patch('homeassistant.ha_client.requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = ha_client.call_service('light', 'turn_on', {"entity_id": "light.living_room"})
        assert result == {"result": "ok"}
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert 'light/turn_on' in args[0]
        assert kwargs['json']["entity_id"] == "light.living_room"
