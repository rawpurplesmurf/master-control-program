from mcp.ollama import create_ollama_prompt


def test_create_ollama_prompt_includes_command_and_entities():
    prompt = create_ollama_prompt(
        "Turn on the living room light",
        {"Living Room Light": "light.living_room"},
        [],
    )

    assert "Turn on the living room light" in prompt
    assert "light.living_room" in prompt
    assert "Living Room Light" in prompt
    assert "Return ONLY the JSON array" in prompt


def test_create_ollama_prompt_contains_response_schema_even_with_rules():
    prompt = create_ollama_prompt(
        "Dim the lights",
        {"Living Room": "light.living_room"},
        [
            {
                "rule_name": "Night dimming",
                "trigger_entity": "light.living_room",
                "target_entity": "light.bedroom",
                "override_keywords": ["manual"],
            }
        ],
    )

    assert '"type": "action" | "check_state"' in prompt
    assert '"entity_id": "string"' in prompt
