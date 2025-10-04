#!/bin/bash

# MCP API Test Script
# This script tests all the endpoints documented in curl.md

BASE_URL="http://localhost:8000"

echo "=== MCP API Test Suite ==="
echo "Testing all endpoints with enhanced rules system"
echo ""

# Check if server is running
if ! curl -s "${BASE_URL}/api/health/db" > /dev/null 2>&1; then
    echo "❌ MCP server is not running at ${BASE_URL}"
    echo "Please start the server with: python -m uvicorn mcp.main:app --host 127.0.0.1 --port 8000"
    exit 1
fi
echo "✅ MCP server is running"
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

# Test Home Assistant Entities
echo "--- Testing Home Assistant Entities ---"

echo "5. Testing HA Entities Endpoint:"
HA_ENTITIES_RESPONSE=$(curl -s "${BASE_URL}/api/ha/entities")
if echo "$HA_ENTITIES_RESPONSE" | jq . > /dev/null 2>&1; then
    ENTITY_COUNT=$(echo "$HA_ENTITIES_RESPONSE" | jq '. | length')
    echo "✅ Successfully retrieved $ENTITY_COUNT HA entities"
    
    # Show domain statistics
    echo "Domain breakdown:"
    echo "$HA_ENTITIES_RESPONSE" | jq -r '
        group_by(.entity_id | split(".")[0]) | 
        map({domain: .[0].entity_id | split(".")[0], count: length}) | 
        sort_by(.count) | reverse | 
        .[] | "  \(.domain): \(.count)"
    ' 2>/dev/null || echo "  Domain analysis failed (jq required)"
    
    # Show sample entities
    echo "Sample entities:"
    echo "$HA_ENTITIES_RESPONSE" | jq -r '
        .[0:3] | .[] | "  \(.entity_id): \(.state) (\(.attributes.friendly_name // "No friendly name"))"
    ' 2>/dev/null || echo "  Entity details failed (jq required)"
else
    echo "❌ Failed to retrieve HA entities"
    echo "$HA_ENTITIES_RESPONSE"
fi
echo ""

# Test Enhanced Rules System (Skippy Guardrails & Submind Automations)
echo "--- Testing Enhanced Rules CRUD ---"

echo "6. Creating a Skippy Guardrail rule:"
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

echo "7. Creating a Submind Automation rule:"
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

echo "8. Listing all rules:"
curl -s "${BASE_URL}/api/rules" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "9. Listing Skippy Guardrail rules only:"
curl -s "${BASE_URL}/api/rules?rule_type=skippy_guardrail" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "10. Listing Submind Automation rules only:"
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

# Test command processing pipeline
echo "--- Testing Command Processing Pipeline ---"

echo "21. First, create a default prompt template for command processing:"
DEFAULT_TEMPLATE_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "test_default",
    "system_prompt": "You are a helpful home automation assistant. Use the provided context to respond to user commands about their smart home devices.",
    "user_prompt_template": "User command: {{user_input}}\n\nCurrent time: {{current_time}}\n\nAvailable devices:\n{{ha_device_status}}\n\nActive rules:\n{{rules_list}}",
    "description": "Default template for command processing pipeline",
    "pre_fetch_data": ["current_time", "ha_device_status", "rules_list"]
  }')
echo "$DEFAULT_TEMPLATE_RESPONSE" | jq '.' || echo "Failed or no jq installed"
DEFAULT_TEMPLATE_ID=$(echo "$DEFAULT_TEMPLATE_RESPONSE" | jq -r '.id' 2>/dev/null || echo "template_id")
echo "Created default template with ID: $DEFAULT_TEMPLATE_ID"
echo ""

echo "22. Testing basic command processing:"
COMMAND_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Turn on the living room light"
  }')
echo "$COMMAND_RESPONSE" | jq '.' || echo "Failed or no jq installed"
echo "Command processing success: $(echo "$COMMAND_RESPONSE" | jq -r '.success' 2>/dev/null || echo "unknown")"
echo ""

echo "23. Testing device status query:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "What lights are currently on in my house?"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "24. Testing complex automation command:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "If it'\''s after sunset, turn on the porch light and set the living room to 30% brightness"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "25. Testing command with source tracking:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Good morning - start my morning routine",
    "source": "test_script"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "26. Testing command processing performance (should show processing_time_ms):"
PERF_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Check system status"
  }')
echo "$PERF_RESPONSE" | jq '.' || echo "Failed or no jq installed"
PROCESSING_TIME=$(echo "$PERF_RESPONSE" | jq -r '.processing_time_ms' 2>/dev/null || echo "unknown")
echo "Processing time: ${PROCESSING_TIME}ms"
echo ""

# Test Prompt History
echo "--- Testing Prompt History ---"

echo "27. Testing prompt history stats:"
curl -s "${BASE_URL}/api/prompt-history/stats" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "28. Testing prompt history retrieval (first 5):"
HISTORY_RESPONSE=$(curl -s "${BASE_URL}/api/prompt-history?limit=5")
echo "$HISTORY_RESPONSE" | jq '.' || echo "Failed or no jq installed"
FIRST_INTERACTION_ID=$(echo "$HISTORY_RESPONSE" | jq -r '.[0].id' 2>/dev/null || echo "")
echo "First interaction ID: $FIRST_INTERACTION_ID"
echo ""

if [ ! -z "$FIRST_INTERACTION_ID" ] && [ "$FIRST_INTERACTION_ID" != "null" ]; then
    echo "29. Testing specific prompt interaction retrieval:"
    curl -s "${BASE_URL}/api/prompt-history/${FIRST_INTERACTION_ID}" | jq '.' || echo "Failed or no jq installed"
    echo ""

    echo "30. Testing prompt re-run:"
    RERUN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/prompt-history/${FIRST_INTERACTION_ID}/rerun")
    echo "$RERUN_RESPONSE" | jq '.' || echo "Failed or no jq installed"
    NEW_INTERACTION_ID=$(echo "$RERUN_RESPONSE" | jq -r '.new_interaction_id' 2>/dev/null || echo "")
    echo "New interaction ID from rerun: $NEW_INTERACTION_ID"
    echo ""
    
    if [ ! -z "$NEW_INTERACTION_ID" ] && [ "$NEW_INTERACTION_ID" != "null" ]; then
        echo "31. Testing prompt history with source filter (rerun):"
        curl -s "${BASE_URL}/api/prompt-history?source=rerun&limit=3" | jq '.' || echo "Failed or no jq installed"
        echo ""
    fi
else
    echo "29-31. Skipping prompt history tests - no interactions found"
    echo ""
fi

echo "32. Testing command with source tracking for prompt history:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Test command for prompt history",
    "source": "test_script"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

# Clean up - delete the test resources
echo "--- Cleanup ---"

echo "33. Deleting the test Skippy Guardrail rule (ID: $GUARDRAIL_ID):"
curl -s -X DELETE "${BASE_URL}/api/rules/${GUARDRAIL_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "34. Deleting the test Submind Automation rule (ID: $AUTOMATION_ID):"
curl -s -X DELETE "${BASE_URL}/api/rules/${AUTOMATION_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "35. Deleting the test data fetcher (ID: $FETCHER_ID):"
curl -s -X DELETE "${BASE_URL}/api/data-fetchers/${FETCHER_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "36. Deleting the test prompt template (ID: $TEMPLATE_ID):"
curl -s -X DELETE "${BASE_URL}/api/prompts/${TEMPLATE_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "37. Deleting the default command processing template (ID: $DEFAULT_TEMPLATE_ID):"
curl -s -X DELETE "${BASE_URL}/api/prompts/${DEFAULT_TEMPLATE_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "38. Cleanup complete - all test resources deleted"
echo ""

echo "=== Test Suite Complete ==="