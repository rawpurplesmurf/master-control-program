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

@patch('mcp.command_processor.process_command_pipeline')
def test_process_command_success(mock_process_command):
    """
    Tests the /api/command endpoint with mocked command processing pipeline.
    """
    # Arrange: Set up the return value for the mocked command processing pipeline
    mock_pipeline_response = {
        "response": "I've turned on the living room light for you.",
        "template_used": "lighting_control", 
        "data_fetchers_executed": ["lights_data"],
        "processing_time_ms": 150,
        "context_keys": ["user_input", "lights_data"],
        "interaction_id": "test-interaction-123",
        "success": True
    }
    mock_process_command.return_value = mock_pipeline_response

    # Act: Call the API endpoint
    response = client.post("/api/command", json={"command": "turn on the living room light"})

    # Assert: Check the response and that our mock was called
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["success"] == True
    assert json_response["response"] == "I've turned on the living room light for you."
    assert json_response["template_used"] == "lighting_control"
    assert json_response["processing_time_ms"] == 150
    mock_process_command.assert_called_once()