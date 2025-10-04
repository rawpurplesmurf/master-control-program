import httpx
from typing import List, Dict, Any

from mcp.config import settings
from mcp.schemas import ExecutedAction

async def execute_actions(actions: List[Dict[str, Any]], rules: List[Dict[str, Any]], user_command: str) -> List[ExecutedAction]:
    headers = {"Authorization": f"Bearer {settings.HA_TOKEN}", "Content-Type": "application/json"}
    executed_list = []

    async with httpx.AsyncClient() as client:
        # This is a simplified implementation. A real implementation would process check_state first.
        for action in actions:
            action_type = action.get("type")
            if action_type == "action":
                intent = action.get("intent")
                entity_id = action.get("entity_id")
                data = action.get("data", {})

                if not intent or not entity_id:
                    continue # Skip malformed actions

                domain, service = intent.split('.')

                # Rule enforcement
                for rule in rules:
                    if rule['trigger_entity'] == entity_id and not any(kw in user_command for kw in rule['override_keywords']):
                        entity_id = rule['target_entity']
                        break

                service_url = f"{settings.HA_URL}/api/services/{domain}/{service}"
                payload = {"entity_id": entity_id, **data}
                response = await client.post(service_url, json=payload, headers=headers, timeout=10)
                response.raise_for_status()
                executed_list.append(ExecutedAction(service=intent, entity_id=entity_id, data=data))
    return executed_list