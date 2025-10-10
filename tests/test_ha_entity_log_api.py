"""
Tests for HA Entity Log API endpoints.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from mcp.main import app


@pytest.fixture
def client():
    """Test client for API endpoints."""
    return TestClient(app)


@pytest.mark.asyncio
class TestHAEntityLogAPI:
    
    async def test_get_entity_log_api_success(self, client):
        """Test successful entity log retrieval via API."""
        entity_id = "light.test_api"
        
        # Mock log entries
        mock_log_entries = [
            {
                "timestamp": "2025-10-03T12:00:00Z",
                "entity_id": entity_id,
                "old_state": {"state": "off"},
                "new_state": {"state": "on"},
                "state_changed": True,
                "attributes_changed": False
            }
        ]
        
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.return_value = mock_log_entries
            
            response = client.get(f"/api/ha/entities/log/{entity_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["entity_id"] == entity_id
            assert data["count"] == 1
            assert len(data["log_entries"]) == 1
            assert data["log_entries"][0]["state_changed"] is True

    async def test_get_entity_log_api_with_params(self, client):
        """Test entity log API with query parameters."""
        entity_id = "switch.test_params"
        
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.return_value = []
            
            # Test with all parameters
            response = client.get(
                f"/api/ha/entities/log/{entity_id}",
                params={
                    "start_date": "2025-10-01T00:00:00Z",
                    "end_date": "2025-10-03T23:59:59Z", 
                    "limit": 50
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["entity_id"] == entity_id
            assert data["count"] == 0
            
            # Verify the function was called with correct parameters (positional args)
            mock_get_log.assert_called_once_with(
                entity_id,
                50,  # limit
                "2025-10-01T00:00:00Z",  # start_date
                "2025-10-03T23:59:59Z"   # end_date
            )

    async def test_get_entity_log_api_invalid_entity(self, client):
        """Test API with invalid entity ID format."""
        # Entity IDs should contain a dot (domain.entity) - but API doesn't validate this
        invalid_entity_id = "invalid_entity_id"
        
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.return_value = []
            
            response = client.get(f"/api/ha/entities/log/{invalid_entity_id}")
            
            assert response.status_code == 200  # API doesn't validate entity format
            data = response.json()
            assert data["entity_id"] == invalid_entity_id

    async def test_get_entity_log_api_invalid_date_format(self, client):
        """Test API with invalid date format."""
        entity_id = "light.test"
        
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.return_value = []  # Function handles invalid dates gracefully
            
            response = client.get(
                f"/api/ha/entities/log/{entity_id}",
                params={"start_date": "invalid-date-format"}
            )
            
            assert response.status_code == 200  # API passes through to function which logs warning
            data = response.json()
            assert data["entity_id"] == entity_id

    async def test_get_entity_log_api_exception_handling(self, client):
        """Test API exception handling."""
        entity_id = "light.test_exception"
        
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.side_effect = Exception("Redis connection failed")
            
            response = client.get(f"/api/ha/entities/log/{entity_id}")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error retrieving entity log" in data["detail"]

    async def test_get_entity_log_summary_api_success(self, client):
        """Test successful entity log summary via API."""
        entity_id = "climate.test_summary"
        
        mock_summary = {
            "entity_id": entity_id,
            "total_changes": 10,
            "state_changes": 5,
            "attribute_changes": 8,
            "change_frequency_per_day": 1.43,
            "most_recent_change": {
                "timestamp": "2025-10-03T12:00:00Z",
                "state_changed": True
            }
        }
        
        with patch('mcp.router.get_entity_log_summary') as mock_get_summary:
            mock_get_summary.return_value = mock_summary
            
            response = client.get(f"/api/ha/entities/log/{entity_id}/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert data == mock_summary

    async def test_get_entity_log_summary_api_with_days(self, client):
        """Test entity log summary API with days parameter."""
        entity_id = "sensor.test_days"
        
        with patch('mcp.router.get_entity_log_summary') as mock_get_summary:
            mock_get_summary.return_value = {"entity_id": entity_id, "total_changes": 0}
            
            response = client.get(
                f"/api/ha/entities/log/{entity_id}/summary",
                params={"days": 14}
            )
            
            assert response.status_code == 200
            
            # Verify function called with correct days parameter (positional arg)
            mock_get_summary.assert_called_once_with(entity_id, 14)

    async def test_get_entity_log_summary_api_invalid_days(self, client):
        """Test summary API with invalid days parameter."""
        entity_id = "light.test"
        
        # Test negative days
        response = client.get(
            f"/api/ha/entities/log/{entity_id}/summary",
            params={"days": -5}
        )
        
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "Input should be greater than or equal to 1" in str(data)
        
        # Test days too large
        response = client.get(
            f"/api/ha/entities/log/{entity_id}/summary",
            params={"days": 50}
        )
        
        assert response.status_code == 422  # FastAPI validation error

    async def test_get_all_entity_logs_api_success(self, client):
        """Test successful retrieval of all entity logs."""
        mock_entities = ["light.living_room", "switch.kitchen", "climate.bedroom"]
        
        with patch('mcp.router.get_all_logged_entities') as mock_get_all:
            mock_get_all.return_value = mock_entities
            
            response = client.get("/api/ha/entities/logs")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 3
            assert set(data["logged_entities"]) == set(mock_entities)

    async def test_get_all_entity_logs_api_with_domain_filter(self, client):
        """Test all entity logs API with domain filtering."""
        all_entities = ["light.living_room", "light.bedroom", "switch.kitchen", "climate.main"]
        filtered_entities = ["light.living_room", "light.bedroom"]
        
        with patch('mcp.router.get_all_logged_entities') as mock_get_all:
            mock_get_all.return_value = all_entities
            
            response = client.get("/api/ha/entities/logs", params={"domain": "light"})
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert set(data["logged_entities"]) == set(filtered_entities)

    async def test_get_all_entity_logs_api_empty_result(self, client):
        """Test all entity logs API with no logged entities."""
        with patch('mcp.router.get_all_logged_entities') as mock_get_all:
            mock_get_all.return_value = []
            
            response = client.get("/api/ha/entities/logs")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
            assert data["logged_entities"] == []

    async def test_get_all_entity_logs_api_exception_handling(self, client):
        """Test exception handling in all entity logs API."""
        with patch('mcp.router.get_all_logged_entities') as mock_get_all:
            mock_get_all.side_effect = Exception("Redis error")
            
            response = client.get("/api/ha/entities/logs")
            
            assert response.status_code == 500
            data = response.json()
            assert "Error getting logged entities" in data["detail"]


    def test_api_parameter_validation_edge_cases(self, client):
        """Test edge cases in parameter validation."""
        entity_id = "sensor.edge_test"
        
        # Test limit edge cases
        response = client.get(
            f"/api/ha/entities/log/{entity_id}",
            params={"limit": 0}
        )
        assert response.status_code == 422  # FastAPI validation error
        
        response = client.get(
            f"/api/ha/entities/log/{entity_id}",
            params={"limit": 1001}  # Over the maximum
        )
        assert response.status_code == 422  # FastAPI validation error
        
        # Test valid boundary values
        with patch('mcp.router.get_entity_log') as mock_get_log:
            mock_get_log.return_value = []
            
            response = client.get(
                f"/api/ha/entities/log/{entity_id}",
                params={"limit": 1}
            )
            assert response.status_code == 200
            
            response = client.get(
                f"/api/ha/entities/log/{entity_id}",
                params={"limit": 1000}  # Maximum allowed
            )
            assert response.status_code == 200