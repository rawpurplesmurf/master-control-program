import asyncio
import pytest

from mcp.action_executor import execute_actions


class DummyResponse:
    def raise_for_status(self) -> None:  # pragma: no cover - trivial helper
        return None


class DummyAsyncClient:
    instance = None

    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        DummyAsyncClient.instance = self
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False

    async def post(self, url, json, headers, timeout):
        self.calls.append({
            "url": url,
            "json": json,
            "headers": headers,
            "timeout": timeout,
        })
        return DummyResponse()


def test_execute_actions_applies_rules(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://home-assistant.local")
    monkeypatch.setenv("HA_TOKEN", "token")
    monkeypatch.setattr("mcp.action_executor.httpx.AsyncClient", DummyAsyncClient)

    actions = [
        {
            "type": "action",
            "intent": "light.turn_on",
            "entity_id": "light.living_room",
            "data": {"brightness": 150},
        }
    ]
    rules = [
        {
            "rule_name": "Redirect living room",
            "trigger_entity": "light.living_room",
            "target_entity": "light.bedroom",
            "override_keywords": [],
        }
    ]

    executed_actions = asyncio.run(
        execute_actions(actions, rules, "turn on the living room light")
    )

    assert executed_actions[0].entity_id == "light.bedroom"
    assert executed_actions[0].service == "light.turn_on"

    call = DummyAsyncClient.instance.calls[0]
    assert call["url"] == "http://home-assistant.local/api/services/light/turn_on"
    assert call["json"]["entity_id"] == "light.bedroom"
    assert call["json"]["brightness"] == 150
