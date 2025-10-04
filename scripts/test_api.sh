#!/bin/bash

# MCP API Test Script
# This script tests all the endpoints documented in curl.md

BASE_URL="http://localhost:8000"

echo "=== MCP API Test Suite ==="
echo "Testing all endpoints from curl.md"
echo ""

# Test healthcheck endpoints first
echo "--- Testing Healthcheck Endpoints ---"

echo "1. Testing Database Health:"
curl -s "${BASE_URL}/api/health/db" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "2. Testing Redis Health:"
curl -s "${BASE_URL}/api/health/redis" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "3. Testing Home Assistant Health:"
curl -s "${BASE_URL}/api/health/ha" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "4. Testing Ollama Health:"
curl -s "${BASE_URL}/api/health/ollama" | jq '.' || echo "Failed or no jq installed"
echo ""

# Test Enhanced Rules System (Skippy Guardrails & Submind Automations)
echo "--- Testing Enhanced Rules CRUD ---"

echo "5. Creating a Skippy Guardrail rule:"
GUARDRAIL_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Test Skippy Guardrail - Garden lights daytime block",
    "rule_type": "skippy_guardrail",
    "description": "Prevent garden lights during daytime hours",
    "target_entity_pattern": "light.garden_*",
    "blocked_actions": ["turn_on"],
    "guard_conditions": {
      "time_after": "06:00",
      "time_before": "18:00"
    },
    "override_keywords": "emergency, force"
  }')
echo "$GUARDRAIL_RESPONSE" | jq '.' || echo "Failed or no jq installed"
GUARDRAIL_ID=$(echo "$GUARDRAIL_RESPONSE" | jq -r '.id' 2>/dev/null || echo "1")
echo "Created Skippy Guardrail with ID: $GUARDRAIL_ID"
echo ""

echo "6. Creating a Submind Automation rule:"
AUTOMATION_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Test Submind Automation - Welcome home lighting",
    "rule_type": "submind_automation",
    "description": "Turn on lights when arriving home after dark",
    "trigger_conditions": {
      "person.john": "home",
      "sun.sun": "below_horizon"
    },
    "target_actions": [
      {
        "service": "light.turn_on",
        "entity_id": "light.living_room",
        "data": {"brightness": 180}
      }
    ]
  }')
echo "$AUTOMATION_RESPONSE" | jq '.' || echo "Failed or no jq installed"
AUTOMATION_ID=$(echo "$AUTOMATION_RESPONSE" | jq -r '.id' 2>/dev/null || echo "2")
echo "Created Submind Automation with ID: $AUTOMATION_ID"
echo ""

echo "7. Listing all rules:"
curl -s "${BASE_URL}/api/rules" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "8. Listing Skippy Guardrail rules only:"
curl -s "${BASE_URL}/api/rules?rule_type=skippy_guardrail" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "9. Listing Submind Automation rules only:"
curl -s "${BASE_URL}/api/rules?rule_type=submind_automation" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "10. Getting specific Skippy Guardrail rule (ID: $GUARDRAIL_ID):"
curl -s "${BASE_URL}/api/rules/${GUARDRAIL_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "11. Getting specific Submind Automation rule (ID: $AUTOMATION_ID):"
curl -s "${BASE_URL}/api/rules/${AUTOMATION_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "12. Updating the Skippy Guardrail rule (ID: $GUARDRAIL_ID):"
curl -s -X PUT "${BASE_URL}/api/rules/${GUARDRAIL_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated: Prevent garden lights during extended daylight hours",
    "guard_conditions": {
      "time_after": "05:30",
      "time_before": "19:00"
    }
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "13. Testing manual execution of Submind Automation (ID: $AUTOMATION_ID):"
curl -s -X POST "${BASE_URL}/api/rules/${AUTOMATION_ID}/execute" | jq '.' || echo "Failed or no jq installed"
echo ""

# Test Data Fetchers CRUD
echo "--- Testing Data Fetchers CRUD ---"

echo "14. Creating a test data fetcher:"
FETCHER_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/data-fetchers" \
  -H "Content-Type: application/json" \
  -d '{
    "fetcher_key": "test_current_weather",
    "description": "Test fetcher for current weather conditions",
    "ttl_seconds": 300,
    "python_code": "import datetime\nresult = {\n    \"timestamp\": datetime.datetime.now().isoformat(),\n    \"weather\": \"sunny\",\n    \"temperature\": 22\n}",
    "is_active": true
  }')
echo "$FETCHER_RESPONSE" | jq '.' || echo "Failed or no jq installed"
FETCHER_ID=$(echo "$FETCHER_RESPONSE" | jq -r '.id' 2>/dev/null || echo "1")
echo "Created data fetcher with ID: $FETCHER_ID"
echo ""

echo "15. Listing all data fetchers:"
curl -s "${BASE_URL}/api/data-fetchers" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "16. Testing data fetcher execution (ID: $FETCHER_ID):"
curl -s -X POST "${BASE_URL}/api/data-fetchers/${FETCHER_ID}/test" | jq '.' || echo "Failed or no jq installed"
echo ""

# Test Prompt Templates CRUD
echo "--- Testing Prompt Templates CRUD ---"

echo "17. Creating a test prompt template:"
TEMPLATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Test Light Control Template",
    "intent_keywords": "light,lamp,brightness,illuminate",
    "system_prompt": "You are a home assistant controller that manages lighting systems.",
    "user_template": "Turn {action} the {entity} in the {location}. Current entities: {ha_device_status}",
    "pre_fetch_data": ["ha_device_status", "current_time"]
  }')
echo "$TEMPLATE_RESPONSE" | jq '.' || echo "Failed or no jq installed"
TEMPLATE_ID=$(echo "$TEMPLATE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "1")
echo "Created template with ID: $TEMPLATE_ID"
echo ""

echo "18. Listing all prompt templates:"
curl -s "${BASE_URL}/api/prompts" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "19. Getting specific prompt template (ID: $TEMPLATE_ID):"
curl -s "${BASE_URL}/api/prompts/${TEMPLATE_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "20. Updating the test template (ID: $TEMPLATE_ID):"
curl -s -X PUT "${BASE_URL}/api/prompts/${TEMPLATE_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Updated Test Light Control Template"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

# Test command processing
echo "--- Testing Command Processing ---"

echo "21. Testing command processing:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Turn on the living room light"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

# Clean up - delete the test resources
echo "--- Cleanup ---"

echo "22. Deleting the test Skippy Guardrail rule (ID: $GUARDRAIL_ID):"
curl -s -X DELETE "${BASE_URL}/api/rules/${GUARDRAIL_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "23. Deleting the test Submind Automation rule (ID: $AUTOMATION_ID):"
curl -s -X DELETE "${BASE_URL}/api/rules/${AUTOMATION_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "24. Deleting the test data fetcher (ID: $FETCHER_ID):"
curl -s -X DELETE "${BASE_URL}/api/data-fetchers/${FETCHER_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "25. Deleting the test prompt template (ID: $TEMPLATE_ID):"
curl -s -X DELETE "${BASE_URL}/api/prompts/${TEMPLATE_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "26. Verifying Skippy Guardrail deletion:"
curl -s "${BASE_URL}/api/rules" | jq ".[] | select(.id==${GUARDRAIL_ID})" || echo "Skippy Guardrail successfully deleted"
echo ""

echo "27. Verifying Submind Automation deletion:"
curl -s "${BASE_URL}/api/rules" | jq ".[] | select(.id==${AUTOMATION_ID})" || echo "Submind Automation successfully deleted"
echo ""

echo "28. Verifying data fetcher deletion:"
curl -s "${BASE_URL}/api/data-fetchers" | jq ".[] | select(.id==${FETCHER_ID})" || echo "Data fetcher successfully deleted"
echo ""

echo "29. Verifying template deletion:"
curl -s "${BASE_URL}/api/prompts" | jq ".[] | select(.id==${TEMPLATE_ID})" || echo "Template successfully deleted"
echo ""

echo "=== Test Suite Complete ==="