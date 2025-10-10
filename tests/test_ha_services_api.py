"""
Tests for Home Assistant Services API endpoints
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from mcp.main import app

@pytest.fixture
def test_client():
    """Create test client for API testing."""
    return TestClient(app)

class TestHAServicesAPI:
    """Test Home Assistant services API endpoints."""

    
    def test_get_services_endpoint(self, test_client):
        """Test GET /api/ha/services endpoint."""
        mock_services = {
            "services": {
                "light": [
                    {
                        "service": "light.turn_on",
                        "name": "turn_on",
                        "description": "Turn on light",
                        "fields": [],
                        "parameters": []
                    }
                ]
            },
            "total_services": 1,
            "total_domains": 1,
            "last_updated": "2023-01-01T12:00:00Z"
        }
        
        with patch('mcp.router.get_ha_services') as mock_get_services:
            mock_get_services.return_value = mock_services
            
            response = test_client.get("/api/ha/services")
            
            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert "light" in data["services"]
            assert data["total_services"] == 1
            assert "cached" in data

    
    def test_get_services_with_refresh(self, test_client):
        """Test GET /api/ha/services with refresh parameter."""
        mock_services = {
            "services": {"test": []},
            "total_services": 0,
            "total_domains": 0
        }
        
        with patch('mcp.router.refresh_ha_services_cache') as mock_refresh:
            mock_refresh.return_value = mock_services
            
            response = test_client.get("/api/ha/services?refresh=true")
            
            assert response.status_code == 200
            mock_refresh.assert_called_once()

    
    def test_get_services_with_domain_filter(self, test_client):
        """Test GET /api/ha/services with domain filter."""
        mock_services = {
            "services": {
                "light": [
                    {"service": "light.turn_on", "name": "turn_on"}
                ],
                "switch": [
                    {"service": "switch.turn_on", "name": "turn_on"}
                ]
            },
            "total_services": 2,
            "total_domains": 2,
            "last_updated": "2023-01-01T12:00:00Z"
        }
        
        with patch('mcp.router.get_ha_services') as mock_get_services:
            mock_get_services.return_value = mock_services
            
            response = test_client.get("/api/ha/services?domain=light")
            
            assert response.status_code == 200
            data = response.json()
            assert data["domain"] == "light"
            assert "light" in data["services"]
            assert "switch" not in data["services"]
            assert data["total_services"] == 1
            assert data["total_domains"] == 1

    
    def test_execute_action_endpoint(self, test_client):
        """Test POST /api/ha/action endpoint."""
        test_action = {
            "service": "light.turn_on",
            "entity_id": "light.living_room",
            "data": {"brightness": 255}
        }
        
        mock_result = {
            "success": True,
            "service": "light.turn_on",
            "entity_id": "light.living_room",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.return_value = mock_result
            
            response = test_client.post("/api/ha/action", json=test_action)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["service"] == "light.turn_on"
            mock_execute.assert_called_once_with(test_action)

    
    def test_execute_action_failure(self, test_client):
        """Test POST /api/ha/action with failure."""
        test_action = {
            "service": "light.turn_on",
            "entity_id": "light.nonexistent"
        }
        
        mock_result = {
            "success": False,
            "error": "Entity not found",
            "service": "light.turn_on"
        }
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.return_value = mock_result
            
            response = test_client.post("/api/ha/action", json=test_action)
            
            assert response.status_code == 200  # Failure is in response body, not HTTP status
            data = response.json()
            assert data["success"] is False
            assert "Entity not found" in data["error"]

    
    def test_execute_bulk_actions_endpoint(self, test_client):
        """Test POST /api/ha/actions/bulk endpoint."""
        test_actions = [
            {"service": "light.turn_on", "entity_id": "light.living_room"},
            {"service": "light.turn_on", "entity_id": "light.bedroom"}
        ]
        
        mock_results = [
            {"success": True, "service": "light.turn_on"},
            {"success": True, "service": "light.turn_on"}
        ]
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.side_effect = mock_results
            
            response = test_client.post("/api/ha/actions/bulk", json=test_actions)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["total_actions"] == 2
            assert data["successful_actions"] == 2
            assert data["failed_actions"] == 0
            assert len(data["results"]) == 2

    
    def test_execute_bulk_actions_too_many(self, test_client):
        """Test POST /api/ha/actions/bulk with too many actions."""
        test_actions = [{"service": "test.service"} for _ in range(51)]
        
        response = test_client.post("/api/ha/actions/bulk", json=test_actions)
        
        assert response.status_code == 400
        data = response.json()
        assert "Too many actions" in data["detail"]

    
    def test_execute_bulk_actions_partial_failure(self, test_client):
        """Test POST /api/ha/actions/bulk with partial failures."""
        test_actions = [
            {"service": "light.turn_on", "entity_id": "light.living_room"},
            {"service": "light.turn_on", "entity_id": "light.nonexistent"}
        ]
        
        mock_results = [
            {"success": True, "service": "light.turn_on"},
            {"success": False, "error": "Entity not found"}
        ]
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.side_effect = mock_results
            
            response = test_client.post("/api/ha/actions/bulk", json=test_actions)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False  # Overall failure due to one failed action
            assert data["total_actions"] == 2
            assert data["successful_actions"] == 1
            assert data["failed_actions"] == 1

    
    def test_get_entity_action_history_endpoint(self, test_client):
        """Test GET /api/ha/entities/{entity_id}/actions endpoint."""
        entity_id = "light.living_room"
        mock_history = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "action": {"service": "light.turn_on"},
                "success": True
            },
            {
                "timestamp": "2023-01-01T11:00:00Z",
                "action": {"service": "light.turn_off"},
                "success": True
            }
        ]
        
        with patch('mcp.router.get_ha_action_history') as mock_get_history:
            mock_get_history.return_value = mock_history
            
            response = test_client.get(f"/api/ha/entities/{entity_id}/actions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["entity_id"] == entity_id
            assert data["count"] == 2
            assert len(data["actions"]) == 2
            assert data["limit"] == 50  # Default limit
            mock_get_history.assert_called_once_with(entity_id, 50)

    
    def test_get_entity_action_history_with_limit(self, test_client):
        """Test GET /api/ha/entities/{entity_id}/actions with custom limit."""
        entity_id = "light.living_room"
        custom_limit = 10
        
        with patch('mcp.router.get_ha_action_history') as mock_get_history:
            mock_get_history.return_value = []
            
            response = test_client.get(f"/api/ha/entities/{entity_id}/actions?limit={custom_limit}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == custom_limit
            mock_get_history.assert_called_once_with(entity_id, custom_limit)

    
    def test_get_entity_action_history_invalid_limit(self, test_client):
        """Test GET /api/ha/entities/{entity_id}/actions with invalid limit."""
        entity_id = "light.living_room"
        
        # Test limit too low
        response = test_client.get(f"/api/ha/entities/{entity_id}/actions?limit=0")
        assert response.status_code == 422
        
        # Test limit too high
        response = test_client.get(f"/api/ha/entities/{entity_id}/actions?limit=300")
        assert response.status_code == 422

    
    def test_services_endpoint_exception_handling(self, test_client):
        """Test exception handling in services endpoint."""
        with patch('mcp.router.get_ha_services') as mock_get_services:
            mock_get_services.side_effect = Exception("Test error")
            
            response = test_client.get("/api/ha/services")
            
            assert response.status_code == 500
            data = response.json()
            assert "Test error" in data["detail"]

    
    def test_action_endpoint_exception_handling(self, test_client):
        """Test exception handling in action endpoint."""
        test_action = {"service": "light.turn_on"}
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            response = test_client.post("/api/ha/action", json=test_action)
            
            assert response.status_code == 500
            data = response.json()
            assert "Test error" in data["detail"]

    
    def test_bulk_actions_endpoint_exception_handling(self, test_client):
        """Test exception handling in bulk actions endpoint."""
        test_actions = [{"service": "light.turn_on"}]
        
        with patch('mcp.router.execute_ha_action') as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            response = test_client.post("/api/ha/actions/bulk", json=test_actions)
            
            assert response.status_code == 500
            data = response.json()
            assert "Test error" in data["detail"]

    
    def test_history_endpoint_exception_handling(self, test_client):
        """Test exception handling in history endpoint."""
        entity_id = "light.living_room"
        
        with patch('mcp.router.get_ha_action_history') as mock_get_history:
            mock_get_history.side_effect = Exception("Test error")
            
            response = test_client.get(f"/api/ha/entities/{entity_id}/actions")
            
            assert response.status_code == 500
            data = response.json()
            assert "Test error" in data["detail"]