import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from datetime import datetime

from mcp.router import router
from mcp.database import get_db

# Mock prompt template model
@dataclass
class MockPromptTemplate:
    id: int
    template_name: str
    intent_keywords: str
    system_prompt: str
    user_template: str
    pre_fetch_data: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

@pytest.fixture
def client():
    mock_db = MagicMock()
    templates = [
        MockPromptTemplate(
            1, 
            "Light Control", 
            "light,lamp,brightness", 
            "You are a home assistant controller",
            "Turn {action} the {entity}",
            '["light.*", "current_time"]',
            datetime(2025, 10, 1, 12, 0, 0),
            datetime(2025, 10, 1, 12, 0, 0)
        ),
        MockPromptTemplate(
            2,
            "Climate Control",
            "temperature,climate,heating",
            "You control the climate system",
            "Set {location} to {temperature}",
            '["climate.*", "weather_data"]',
            datetime(2025, 10, 1, 12, 0, 0),
            datetime(2025, 10, 1, 12, 0, 0)
        )
    ]
    
    def query_side_effect(model):
        class Query:
            def all(self_inner):
                return templates
            def filter(self_inner, *args, **kwargs):
                class FilteredQuery:
                    def first(self_inner2):
                        return templates[0] if templates else None
                return FilteredQuery()
            def first(self_inner):
                all_items = self_inner.all()
                return all_items[0] if all_items else None
        return Query()
    
    mock_db.query.side_effect = query_side_effect
    mock_db.add.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None
    mock_db.delete.return_value = None
    
    def override_get_db():
        yield mock_db
    
    # Patch the PromptTemplate model constructor and formatter
    with patch("mcp.router.models.PromptTemplate", side_effect=lambda **kwargs: MockPromptTemplate(id=99, **kwargs)), \
         patch("mcp.router._format_prompt_template_response", side_effect=lambda t: {
             "id": t.id,
             "template_name": t.template_name,
             "intent_keywords": t.intent_keywords,
             "system_prompt": t.system_prompt,
             "user_template": t.user_template,
             "pre_fetch_data": json.loads(t.pre_fetch_data) if isinstance(t.pre_fetch_data, str) else t.pre_fetch_data,
             "created_at": t.created_at.isoformat() if hasattr(t, 'created_at') and t.created_at else "2025-10-01T12:00:00",
             "updated_at": t.updated_at.isoformat() if hasattr(t, 'updated_at') and t.updated_at else "2025-10-01T12:00:00"
         }):
        test_app = FastAPI()
        test_app.include_router(router)  # No prefix since routes already have /api/
        test_app.dependency_overrides[get_db] = override_get_db
        with TestClient(test_app) as c:
            yield c

def test_list_prompt_templates(client):
    response = client.get("/api/prompts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["template_name"] == "Light Control"

def test_create_prompt_template(client):
    template = {
        "template_name": "Test Template",
        "intent_keywords": "test,sample",
        "system_prompt": "You are a test controller",
        "user_template": "Execute {action}",
        "pre_fetch_data": ["test.*", "system_status"]
    }
    response = client.post("/api/prompts", json=template)
    assert response.status_code == 201

def test_get_prompt_template(client):
    response = client.get("/api/prompts/1")
    assert response.status_code == 200
    data = response.json()
    assert data["template_name"] == "Light Control"

def test_update_prompt_template(client):
    update = {"template_name": "Updated Light Control"}
    response = client.put("/api/prompts/1", json=update)
    assert response.status_code == 200

def test_delete_prompt_template(client):
    response = client.delete("/api/prompts/1")
    assert response.status_code == 204