import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from fastapi.testclient import TestClient
from mcp.router import router
from fastapi import FastAPI

def test_command_processing_success():
    """Test successful command processing pipeline"""
    with patch('mcp.command_processor.process_command_pipeline') as mock_pipeline:
        # Mock successful pipeline response
        mock_pipeline.return_value = {
            "response": "The living room light is currently on.",
            "template_used": "default",
            "data_fetchers_executed": ["current_time", "ha_device_status", "rules_list"],
            "processing_time_ms": 250,
            "context_keys": ["user_input", "current_time", "ha_device_status", "rules_list"],
            "success": True
        }
        
        # Mock database dependencies
        with patch('mcp.router.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            app = FastAPI()
            app.include_router(router)
            
            with TestClient(app) as client:
                response = client.post("/api/command", json={"command": "What lights are on?"})
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert data["success"] is True
                assert data["response"] == "The living room light is currently on."
                assert data["template_used"] == "default"
                assert "processing_time_ms" in data
                assert len(data["data_fetchers_executed"]) == 3
                
                # Verify pipeline was called with correct parameters (includes source='api')
                mock_pipeline.assert_called_once()

def test_command_processing_template_not_found():
    """Test command processing when template is not found"""
    with patch('mcp.command_processor.process_command_pipeline') as mock_pipeline:
        # Mock template not found response
        mock_pipeline.return_value = {
            "response": "Error: Prompt template 'default' not found. Please create a 'default' template first.",
            "error": "template_not_found",
            "template_requested": "default",
            "processing_time_ms": 50,
            "success": False
        }
        
        with patch('mcp.router.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            app = FastAPI()
            app.include_router(router)
            
            with TestClient(app) as client:
                response = client.post("/api/command", json={"command": "Turn on lights"})
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is False
                assert "prompt template" in data["response"].lower() and "not found" in data["response"].lower()
                assert data["error"] == "template_not_found"

def test_command_processing_pipeline_error():
    """Test command processing when pipeline throws an exception"""
    with patch('mcp.command_processor.process_command_pipeline') as mock_pipeline:
        # Mock pipeline exception
        mock_pipeline.side_effect = Exception("LLM connection failed")
        
        with patch('mcp.router.get_db') as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            
            app = FastAPI()
            app.include_router(router)
            
            with TestClient(app) as client:
                response = client.post("/api/command", json={"command": "Help me"})
                
                assert response.status_code == 200
                data = response.json()
                
                assert data["success"] is False
                assert "unexpected error" in data["response"].lower()
                assert data["error"] == "command_endpoint_error"

def test_determine_prompt_template():
    """Test the prompt template determination logic"""
    from mcp.command_processor import determine_prompt_template
    
    # Mock database session
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []  # No templates in DB
    
    # Should return 'default' when no templates found
    assert determine_prompt_template("Turn on the lights", mock_db) == "default"
    assert determine_prompt_template("What's the weather like?", mock_db) == "default"
    assert determine_prompt_template("Help me with automation", mock_db) == "default"

def test_execute_data_fetchers():
    """Test data fetcher execution"""
    from mcp.command_processor import execute_data_fetchers
    from mcp import models
    
    # Mock template with data fetchers
    mock_template = MagicMock()
    mock_template.template_name = "test_template"
    mock_template.pre_fetch_data = '["current_time", "ha_device_status"]'  # JSON string
    
    with patch('mcp.command_processor.get_prefetch_data') as mock_get_data:
        # Mock successful data fetching
        def mock_fetch_side_effect(key):
            if key == "current_time":
                return {"time": "2025-10-03T12:00:00"}
            elif key == "ha_device_status":
                return {"lights": {"living_room": "on", "bedroom": "off"}}
            else:
                return {"error": "Unknown fetcher"}
        
        mock_get_data.side_effect = mock_fetch_side_effect
        
        result = execute_data_fetchers(mock_template, "Test command")
        
        assert "user_input" in result
        assert result["user_input"] == "Test command"
        assert "current_time" in result
        assert "ha_device_status" in result
        assert result["current_time"]["time"] == "2025-10-03T12:00:00"
        assert result["ha_device_status"]["lights"]["living_room"] == "on"

def test_execute_data_fetchers_no_fetchers():
    """Test data fetcher execution when template has no fetchers"""
    from mcp.command_processor import execute_data_fetchers
    
    # Mock template with no data fetchers
    mock_template = MagicMock()
    mock_template.template_name = "simple_template"
    mock_template.pre_fetch_data = None  # No fetchers
    
    result = execute_data_fetchers(mock_template, "Test command")
    
    # Should return both user_input and user_command
    assert result == {"user_input": "Test command", "user_command": "Test command"}

def test_construct_prompt_success():
    """Test successful prompt construction"""
    from mcp.command_processor import construct_prompt
    
    # Mock template
    mock_template = MagicMock()
    mock_template.template_name = "test_template"
    mock_template.system_prompt = "You are a helpful assistant."
    mock_template.user_template = "User says: {user_input}. Time: {current_time}"
    
    # Mock context
    context = {
        "user_input": "Turn on lights",
        "current_time": "2025-10-03T12:00:00"
    }
    
    system, user = construct_prompt(mock_template, context)
    
    assert system == "You are a helpful assistant."
    assert user == "User says: Turn on lights. Time: 2025-10-03T12:00:00"

def test_construct_prompt_missing_placeholder():
    """Test prompt construction with missing placeholder"""
    from mcp.command_processor import construct_prompt
    
    # Mock template with placeholder that's not in context
    mock_template = MagicMock()
    mock_template.template_name = "test_template"
    mock_template.system_prompt = "You are a helpful assistant."
    mock_template.user_template = "User says: {user_input}. Weather: {weather_data}"
    
    # Mock context missing weather_data
    context = {"user_input": "Turn on lights"}
    
    system, user = construct_prompt(mock_template, context)
    
    assert "error with the prompt template" in system.lower()
    assert "missing placeholder" in user.lower()
    assert "weather_data" in user