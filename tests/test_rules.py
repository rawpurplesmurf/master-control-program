
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
import pytest
from unittest.mock import patch
from dataclasses import dataclass, asdict
from mcp.router import router
from mcp.database import get_db

# Mock database dependency for rules
@dataclass
class MockRule:
    id: int
    rule_name: str
    trigger_entity: str
    target_entity: str
    override_keywords: str = None

@pytest.fixture
def client():
    mock_db = MagicMock()
    rules = [
        MockRule(1, "No lights after midnight", "skippy", "light.living_room", "manual,override"),
        MockRule(2, "No AC if window open", "window_sensor", "climate.bedroom", None)
    ]
    def query_side_effect(model):
        class Query:
            def all(self_inner):
                return rules
            def filter(self_inner, *args, **kwargs):
                class FilteredQuery:
                    def all(self_inner2):
                        return rules
                    def first(self_inner2):
                        return rules[0]
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
    # Patch only the constructor of models.Rule
    with patch("mcp.router.models.Rule", side_effect=lambda **kwargs: MockRule(id=99, **kwargs)):
        test_app = FastAPI()
        test_app.include_router(router)  # No prefix since routes already have /api/
        test_app.dependency_overrides[get_db] = override_get_db
        with TestClient(test_app) as c:
            yield c

def test_list_rules(client):
    response = client.get("/api/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["rule_name"] == "No lights after midnight"

def test_create_rule(client):
    rule = {
        "rule_name": "Test rule",
        "trigger_entity": "sensor",
        "target_entity": "light.test",
        "override_keywords": "manual"
    }
    response = client.post("/api/rules", json=rule)
    assert response.status_code == 200
    data = response.json()
    assert data["rule_name"] == "Test rule"

def test_update_rule(client):
    update = {"rule_name": "Updated rule"}
    response = client.put("/api/rules/1", json=update)
    assert response.status_code == 200
    data = response.json()
    assert data["rule_name"] == "Updated rule"

def test_delete_rule(client):
    response = client.delete("/api/rules/1")
    assert response.status_code == 200
    data = response.json()
    assert data["detail"] == "Rule deleted"
