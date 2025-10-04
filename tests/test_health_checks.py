import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from mcp.router import router

@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.include_router(router)  # No prefix since routes already have /api/
    return TestClient(test_app)

@patch('mcp.router.check_mysql_connection')
def test_health_db_success(mock_check_mysql, client):
    mock_check_mysql.return_value = None  # No exception means success
    
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('mcp.router.check_mysql_connection')
def test_health_db_error(mock_check_mysql, client):
    mock_check_mysql.side_effect = Exception("Connection failed")
    
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["detail"] == "Connection failed"

@patch('mcp.router.check_redis_connection')
@pytest.mark.asyncio
async def test_health_redis_success(mock_check_redis, client):
    mock_check_redis.return_value = AsyncMock()
    
    response = client.get("/api/health/redis")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('mcp.router.check_redis_connection')
@pytest.mark.asyncio 
async def test_health_redis_error(mock_check_redis, client):
    mock_check_redis.side_effect = Exception("Redis connection failed")
    
    response = client.get("/api/health/redis")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["detail"] == "Redis connection failed"

@patch('mcp.router.check_home_assistant_connection')
@pytest.mark.asyncio
async def test_health_ha_success(mock_check_ha, client):
    mock_check_ha.return_value = AsyncMock()
    
    response = client.get("/api/health/ha")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('mcp.router.check_home_assistant_connection')
@pytest.mark.asyncio
async def test_health_ha_error(mock_check_ha, client):
    mock_check_ha.side_effect = Exception("HA connection failed")
    
    response = client.get("/api/health/ha")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["detail"] == "HA connection failed"

@patch('mcp.router.check_home_assistant_connection')
@pytest.mark.asyncio
async def test_health_homeassistant_alias(mock_check_ha, client):
    """Test that /api/health/homeassistant is an alias for /api/health/ha"""
    mock_check_ha.return_value = AsyncMock()
    
    response = client.get("/api/health/homeassistant")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('mcp.router.check_ollama_connection')
@pytest.mark.asyncio
async def test_health_ollama_success(mock_check_ollama, client):
    mock_check_ollama.return_value = AsyncMock()
    
    response = client.get("/api/health/ollama")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

@patch('mcp.router.check_ollama_connection')
@pytest.mark.asyncio
async def test_health_ollama_error(mock_check_ollama, client):
    mock_check_ollama.side_effect = Exception("Ollama connection failed")
    
    response = client.get("/api/health/ollama")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert data["detail"] == "Ollama connection failed"