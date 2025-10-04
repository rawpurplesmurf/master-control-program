import pytest
from unittest.mock import AsyncMock, patch

from mcp.action_executor import execute_actions
from mcp.schemas import ExecutedAction

@pytest.mark.asyncio
async def test_execute_actions_success():
    """
    Tests that execute_actions correctly forms and sends a request to Home Assistant.
    """
    # Mock the httpx.AsyncClient
    mock_async_client = AsyncMock()
    mock_async_client.post.return_value.raise_for_status = AsyncMock()

    # The actions we expect to receive from Ollama
    ollama_actions = [
        {
            "type": "action",
            "intent": "light.turn_on",
            "entity_id": "light.living_room",
            "data": {"brightness": 255}
        }
    ]

    with patch('mcp.action_executor.httpx.AsyncClient') as mock_client_class:
        mock_client_class.return_value.__aenter__.return_value = mock_async_client
        result = await execute_actions(actions=ollama_actions, rules=[], user_command="turn on light")

        # Verify that httpx.post was called with the correct URL and payload
        mock_async_client.post.assert_called_once()
        call_args = mock_async_client.post.call_args
        assert "/api/services/light/turn_on" in call_args[0][0]
        assert call_args[1]['json'] == {"entity_id": "light.living_room", "brightness": 255}
        assert len(result) == 1
        assert isinstance(result[0], ExecutedAction)