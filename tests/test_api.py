from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from mcp.main import app
from mcp.database import get_db

# Mock database dependency
def override_get_db():
    mock_db = MagicMock()
    # Mock the query results for entities and rules
    mock_db.query.return_value.all.return_value = []
    try:
        yield mock_db
    finally:
        pass

# Apply the override to the app
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@patch('mcp.router.models.PromptHistory')
@patch('mcp.router.call_ollama')
@patch('mcp.router.execute_actions')
def test_process_command_success(mock_execute_actions, mock_call_ollama, mock_prompt_history):
    """
    Tests the /api/command endpoint with mocked external services.
    """
    # Arrange: Set up the return values for our mocked functions
    mock_ollama_response = [
        {
            "type": "action",
            "intent": "light.turn_on",
            "entity_id": "light.living_room",
            "data": {}
        }
    ]
    mock_call_ollama.return_value = mock_ollama_response

    # We need to import the schema here to avoid circular dependencies at load time
    from mcp.schemas import ExecutedAction
    mock_executed_actions = [ExecutedAction(service="light.turn_on", entity_id="light.living_room", data={})]
    mock_execute_actions.return_value = mock_executed_actions

    # Act: Call the API endpoint
    response = client.post("/api/command", json={"command": "turn on the living room light"})

    # Assert: Check the response and that our mocks were called
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "success"
    assert len(json_response["executed_actions"]) == 1
    assert json_response["executed_actions"][0]["entity_id"] == "light.living_room"
    mock_call_ollama.assert_called_once()
    mock_execute_actions.assert_called_once()