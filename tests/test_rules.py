
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
    rule_type: str
    description: str = None
    is_active: int = 1
    priority: int = 0
    target_entity_pattern: str = None
    blocked_actions: str = "[]"
    guard_conditions: str = "{}"
    trigger_conditions: str = "{}"
    target_actions: str = "[]"
    override_keywords: str = None
    execution_schedule: str = None
    created_at: str = None
    updated_at: str = None
    last_executed: str = None

@pytest.fixture
def client():
    mock_db = MagicMock()
    rules = [
        MockRule(id=1, rule_name="No lights after midnight", rule_type="skippy_guardrail", 
                target_entity_pattern="light.living_room", override_keywords="manual,override"),
        MockRule(id=2, rule_name="No AC if window open", rule_type="submind_automation",
                trigger_conditions='{"entity_id": "binary_sensor.window", "state": "on"}',
                target_actions='[{"service": "climate.turn_off", "entity_id": "climate.bedroom"}]')
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
        "rule_type": "skippy_guardrail",
        "description": "Test rule description",
        "target_entity_pattern": "light.test",
        "blocked_actions": ["turn_on"],
        "guard_conditions": {"time_range": {"from": "22:00", "to": "06:00"}},
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
