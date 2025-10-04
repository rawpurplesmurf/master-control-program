import pytest
from unittest.mock import patch, MagicMock
import json
from fastapi.testclient import TestClient
from mcp.router import router
from fastapi import FastAPI

def test_get_ha_entities():
    """Test the HA entities endpoint"""
    # Mock the Redis and requests dependencies
    with patch('redis.Redis') as mock_redis_class, \
         patch('requests.get') as mock_requests_get, \
         patch('os.environ.get') as mock_env_get:
        
        # Configure mocks
        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis
        
        # Mock environment variables
        mock_env_get.side_effect = lambda key, default=None: {
            'REDIS_URL': 'redis://localhost:6379/0',
            'HA_URL': 'http://localhost:8123',
            'HA_TOKEN': 'test_token'
        }.get(key, default)
        
        # Test case 1: Entities in Redis cache
        mock_entities = [
            {
                "entity_id": "light.test_light",
                "state": "on",
                "attributes": {"friendly_name": "Test Light"},
                "last_changed": "2025-10-03T12:00:00"
            },
            {
                "entity_id": "switch.test_switch", 
                "state": "off",
                "attributes": {"friendly_name": "Test Switch"},
                "last_changed": "2025-10-03T11:00:00"
            }
        ]
        
        mock_redis.get.return_value = json.dumps(mock_entities).encode()
        
        # Create test app
        app = FastAPI()
        app.include_router(router)
        
        with TestClient(app) as client:
            response = client.get("/api/ha/entities")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["entity_id"] == "light.test_light"
            assert data[1]["entity_id"] == "switch.test_switch"
            
        # Test case 2: No cache, fetch from HA API
        mock_redis.get.return_value = None
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = mock_entities
        mock_requests_get.return_value = mock_response
        
        with TestClient(app) as client:
            response = client.get("/api/ha/entities")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["entity_id"] == "light.test_light"
            
            # Verify HA API was called
            mock_requests_get.assert_called_with(
                "http://localhost:8123/api/states",
                headers={
                    "Authorization": "Bearer test_token",
                    "Content-Type": "application/json",
                },
                timeout=10
            )
            
            # Verify result was cached
            mock_redis.set.assert_called()

def test_get_ha_entities_redis_error():
    """Test HA entities endpoint with Redis connection error"""
    with patch('redis.Redis') as mock_redis_class:
        # Import redis to get the RedisError exception
        import redis
        mock_redis_class.from_url.side_effect = redis.RedisError("Redis connection failed")
        
        app = FastAPI()
        app.include_router(router)
        
        with TestClient(app) as client:
            response = client.get("/api/ha/entities")
            
            assert response.status_code == 503
            data = response.json()
            assert "Redis connection error" in data["detail"]

def test_get_ha_entities_ha_api_error():
    """Test HA entities endpoint with HA API error"""
    with patch('redis.Redis') as mock_redis_class, \
         patch('requests.get') as mock_requests_get, \
         patch('os.environ.get') as mock_env_get:
        
        # Configure mocks
        mock_redis = MagicMock()
        mock_redis_class.from_url.return_value = mock_redis
        mock_redis.get.return_value = None  # No cache
        
        mock_env_get.side_effect = lambda key, default=None: {
            'REDIS_URL': 'redis://localhost:6379/0',
            'HA_URL': 'http://localhost:8123',
            'HA_TOKEN': 'test_token'
        }.get(key, default)
        
        # Mock HA API failure
        import requests
        mock_requests_get.side_effect = requests.RequestException("HA API connection failed")
        
        app = FastAPI()
        app.include_router(router)
        
        with TestClient(app) as client:
            response = client.get("/api/ha/entities")
            
            assert response.status_code == 503
            data = response.json()
            assert "Home Assistant connection error" in data["detail"]