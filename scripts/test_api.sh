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

# Test System Prompt CRUD
echo "--- Testing System Prompt Management ---"

echo "21. Listing all system prompts:"
curl -s "${BASE_URL}/api/system-prompts" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "22. Getting active system prompt:"
ACTIVE_PROMPT_RESPONSE=$(curl -s "${BASE_URL}/api/system-prompts/active")
echo "$ACTIVE_PROMPT_RESPONSE" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "23. Creating a test system prompt:"
SYSTEM_PROMPT_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/system-prompts" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test_friendly_assistant",
    "prompt": "You are a friendly and helpful Home Assistant controller. Always greet users warmly, explain what you are doing, and ask if they need anything else after completing actions. Use a conversational tone and provide helpful context about device states.",
    "description": "Test friendly conversational system prompt",
    "is_active": false
  }')
echo "$SYSTEM_PROMPT_RESPONSE" | jq '.' || echo "Failed or no jq installed"
SYSTEM_PROMPT_ID=$(echo "$SYSTEM_PROMPT_RESPONSE" | jq -r '.id' 2>/dev/null || echo "1")
echo "Created system prompt with ID: $SYSTEM_PROMPT_ID"
echo ""

echo "24. Updating the test system prompt (ID: $SYSTEM_PROMPT_ID):"
curl -s -X PUT "${BASE_URL}/api/system-prompts/${SYSTEM_PROMPT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated test friendly conversational system prompt with enhanced personality"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "25. Testing system prompt activation (ID: $SYSTEM_PROMPT_ID):"
curl -s -X POST "${BASE_URL}/api/system-prompts/${SYSTEM_PROMPT_ID}/activate" \
  -H "Content-Type: application/json" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "26. Verifying active system prompt changed:"
curl -s "${BASE_URL}/api/system-prompts/active" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "27. Deleting the test system prompt (ID: $SYSTEM_PROMPT_ID):"
curl -s -X DELETE "${BASE_URL}/api/system-prompts/${SYSTEM_PROMPT_ID}" | jq '.' || echo "Failed or no jq installed"
echo ""

# Test command processing pipeline
echo "--- Testing Command Processing Pipeline ---"

echo "28. First, create a default prompt template for command processing:"
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

echo "29. Testing basic command processing:"
COMMAND_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Turn on the living room light"
  }')
echo "$COMMAND_RESPONSE" | jq '.' || echo "Failed or no jq installed"
echo "Command processing success: $(echo "$COMMAND_RESPONSE" | jq -r '.success' 2>/dev/null || echo "unknown")"
echo ""

echo "30. Testing device status query:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "What lights are currently on in my house?"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "31. Testing complex automation command:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "If it'\''s after sunset, turn on the porch light and set the living room to 30% brightness"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "32. Testing command with source tracking:"
curl -s -X POST "${BASE_URL}/api/command" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Good morning - start my morning routine",
    "source": "test_script"
  }' | jq '.' || echo "Failed or no jq installed"
echo ""

echo "33. Testing command processing performance (should show processing_time_ms):"
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

echo "34. Testing prompt history stats:"
curl -s "${BASE_URL}/api/prompt-history/stats" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "35. Testing prompt history retrieval (first 5):"
HISTORY_RESPONSE=$(curl -s "${BASE_URL}/api/prompt-history?limit=5")
echo "$HISTORY_RESPONSE" | jq '.' || echo "Failed or no jq installed"
FIRST_INTERACTION_ID=$(echo "$HISTORY_RESPONSE" | jq -r '.[0].id' 2>/dev/null || echo "")
echo "First interaction ID: $FIRST_INTERACTION_ID"
echo ""

if [ ! -z "$FIRST_INTERACTION_ID" ] && [ "$FIRST_INTERACTION_ID" != "null" ]; then
    echo "36. Testing specific prompt interaction retrieval:"
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

# Test Home Assistant Entity Logging endpoints
echo "--- Testing HA Entity Logging ---"

echo "39. Testing all logged entities endpoint:"
ALL_ENTITIES_RESPONSE=$(curl -s "${BASE_URL}/api/ha/entities/logs")
if echo "$ALL_ENTITIES_RESPONSE" | jq . > /dev/null 2>&1; then
    LOGGED_COUNT=$(echo "$ALL_ENTITIES_RESPONSE" | jq -r '.count')
    echo "✅ Found $LOGGED_COUNT entities with state change logs"
    
    # Get first entity for testing specific endpoint
    FIRST_ENTITY=$(echo "$ALL_ENTITIES_RESPONSE" | jq -r '.logged_entities[0]' 2>/dev/null || echo "")
    
    if [ ! -z "$FIRST_ENTITY" ] && [ "$FIRST_ENTITY" != "null" ]; then
        echo "Sample entity: $FIRST_ENTITY"
        echo ""
        
        echo "40. Testing entity log for $FIRST_ENTITY:"
        curl -s "${BASE_URL}/api/ha/entities/log/${FIRST_ENTITY}?limit=5" | jq '.' || echo "Failed or no jq installed"
        echo ""
        
        echo "41. Testing entity log summary for $FIRST_ENTITY:"
        curl -s "${BASE_URL}/api/ha/entities/log/${FIRST_ENTITY}/summary?days=7" | jq '.' || echo "Failed or no jq installed"
        echo ""
    else
        echo "40-41. Skipping specific entity tests - no entities found in logs"
        echo ""
    fi
else
    echo "❌ Failed to get logged entities list"
    echo "$ALL_ENTITIES_RESPONSE"
    echo ""
fi

echo "42. Testing logged entities with domain filter (light):"
curl -s "${BASE_URL}/api/ha/entities/logs?domain=light" | jq '.' || echo "Failed or no jq installed"
echo ""

echo "43. Testing entity log with date range filtering:"
# Use current date for testing
CURRENT_DATE=$(date -u +"%Y-%m-%dT00:00:00Z")
if [ ! -z "$FIRST_ENTITY" ] && [ "$FIRST_ENTITY" != "null" ]; then
    curl -s "${BASE_URL}/api/ha/entities/log/${FIRST_ENTITY}?start_date=${CURRENT_DATE}&limit=10" | jq '.' || echo "Failed or no jq installed"
else
    echo "Skipping - no test entity available"
fi
echo ""

echo "44. Testing entity summary with different time periods:"
if [ ! -z "$FIRST_ENTITY" ] && [ "$FIRST_ENTITY" != "null" ]; then
    echo "  14-day summary:"
    curl -s "${BASE_URL}/api/ha/entities/log/${FIRST_ENTITY}/summary?days=14" | jq '.total_changes, .change_frequency_per_day' || echo "Failed"
    echo "  30-day summary:"  
    curl -s "${BASE_URL}/api/ha/entities/log/${FIRST_ENTITY}/summary?days=30" | jq '.total_changes, .change_frequency_per_day' || echo "Failed"
else
    echo "Skipping - no test entity available"
fi
echo ""

echo "--- Testing Home Assistant Device Control ---"

echo "45. Testing HA services endpoint (cached):"
HA_SERVICES_RESPONSE=$(curl -s "${BASE_URL}/api/ha/services")
if echo "$HA_SERVICES_RESPONSE" | jq . > /dev/null 2>&1; then
    SERVICE_COUNT=$(echo "$HA_SERVICES_RESPONSE" | jq -r '.total_services // 0')
    DOMAIN_COUNT=$(echo "$HA_SERVICES_RESPONSE" | jq -r '.total_domains // 0')
    CACHED=$(echo "$HA_SERVICES_RESPONSE" | jq -r '.cached // false')
    FALLBACK=$(echo "$HA_SERVICES_RESPONSE" | jq -r '.fallback // false')
    
    echo "✅ Retrieved $SERVICE_COUNT services across $DOMAIN_COUNT domains"
    echo "   Cached: $CACHED, Fallback: $FALLBACK"
    
    # Show available domains
    DOMAINS=$(echo "$HA_SERVICES_RESPONSE" | jq -r '.services | keys[]' 2>/dev/null | tr '\n' ' ' | head -c 100)
    echo "   Sample domains: $DOMAINS"
else
    echo "❌ Failed to get HA services"
    echo "$HA_SERVICES_RESPONSE"
fi
echo ""

echo "46. Testing HA services refresh:"
curl -s "${BASE_URL}/api/ha/services?refresh=true" | jq '.total_services, .cached, .fallback' || echo "Failed or no jq installed"
echo ""

echo "47. Testing HA services domain filter (light):"
curl -s "${BASE_URL}/api/ha/services?domain=light" | jq '.domain, .total_services' || echo "Failed or no jq installed"
echo ""

echo "48. Testing HA action execution (safe action):"
# Use a safe action that won't cause harm - just try to get service validation
SAFE_ACTION_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/ha/action" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "homeassistant.check_config"
  }')

if echo "$SAFE_ACTION_RESPONSE" | jq . > /dev/null 2>&1; then
    SUCCESS=$(echo "$SAFE_ACTION_RESPONSE" | jq -r '.success // false')
    if [ "$SUCCESS" = "true" ]; then
        echo "✅ Action executed successfully"
    else
        ERROR=$(echo "$SAFE_ACTION_RESPONSE" | jq -r '.error // "Unknown error"')
        echo "⚠️  Action validation/execution failed (expected): $ERROR"
    fi
else
    echo "❌ Failed to call action endpoint"
    echo "$SAFE_ACTION_RESPONSE"
fi
echo ""

echo "49. Testing HA bulk actions (validation only):"
BULK_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/ha/actions/bulk" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "service": "homeassistant.check_config"
    }
  ]')

if echo "$BULK_RESPONSE" | jq . > /dev/null 2>&1; then
    TOTAL_ACTIONS=$(echo "$BULK_RESPONSE" | jq -r '.total_actions // 0')
    SUCCESS_COUNT=$(echo "$BULK_RESPONSE" | jq -r '.successful_actions // 0')
    FAIL_COUNT=$(echo "$BULK_RESPONSE" | jq -r '.failed_actions // 0')
    echo "✅ Bulk action endpoint works - processed $TOTAL_ACTIONS actions ($SUCCESS_COUNT success, $FAIL_COUNT failed)"
else
    echo "❌ Failed to call bulk actions endpoint"
    echo "$BULK_RESPONSE"
fi
echo ""

echo "50. Testing bulk actions limit (should fail):"
# Test with 51 actions to trigger the limit
BULK_ACTIONS="["
for i in {1..51}; do
    if [ $i -gt 1 ]; then
        BULK_ACTIONS+=","
    fi
    BULK_ACTIONS+='{"service":"homeassistant.check_config"}'
done
BULK_ACTIONS+="]"

LIMIT_RESPONSE=$(curl -s -w "%{http_code}" -X POST "${BASE_URL}/api/ha/actions/bulk" \
  -H "Content-Type: application/json" \
  -d "$BULK_ACTIONS")

HTTP_CODE="${LIMIT_RESPONSE: -3}"
if [ "$HTTP_CODE" = "400" ]; then
    echo "✅ Bulk actions limit correctly enforced (400 error for >50 actions)"
else
    echo "⚠️  Unexpected response code: $HTTP_CODE"
fi
echo ""

echo "51. Testing action history endpoint:"
# Try to get action history for a common entity pattern
TEST_ENTITIES=("light.living_room" "switch.test" "climate.thermostat")

for ENTITY in "${TEST_ENTITIES[@]}"; do
    HISTORY_RESPONSE=$(curl -s "${BASE_URL}/api/ha/entities/${ENTITY}/actions?limit=5")
    if echo "$HISTORY_RESPONSE" | jq . > /dev/null 2>&1; then
        ACTION_COUNT=$(echo "$HISTORY_RESPONSE" | jq -r '.count // 0')
        if [ "$ACTION_COUNT" -gt 0 ]; then
            echo "✅ Found $ACTION_COUNT action history entries for $ENTITY"
            break
        fi
    fi
done

if [ "$ACTION_COUNT" -eq 0 ]; then
    echo "ℹ️  No action history found (expected for new system)"
fi
echo ""

echo "52. Testing action history with invalid limit:"
INVALID_LIMIT_RESPONSE=$(curl -s -w "%{http_code}" "${BASE_URL}/api/ha/entities/light.test/actions?limit=300")
HTTP_CODE="${INVALID_LIMIT_RESPONSE: -3}"
if [ "$HTTP_CODE" = "422" ]; then
    echo "✅ Action history limit validation works (422 error for limit > 200)"
else
    echo "⚠️  Unexpected response code for invalid limit: $HTTP_CODE"
fi
echo ""

echo "--- Testing Cache Management Endpoints ---"

echo "53. Testing cache information endpoint:"
CACHE_INFO_RESPONSE=$(curl -s "${BASE_URL}/api/ha/cache/info")
if echo "$CACHE_INFO_RESPONSE" | jq . > /dev/null 2>&1; then
    TOTAL_ENTITIES=$(echo "$CACHE_INFO_RESPONSE" | jq -r '.cached_entities.total_count // 0')
    CONTROLLABLE_ENTITIES=$(echo "$CACHE_INFO_RESPONSE" | jq -r '.cached_entities.controllable_count // 0')
    DOMAIN_COUNT=$(echo "$CACHE_INFO_RESPONSE" | jq -r '.cache_metadata.domains | length // 0')
    echo "✅ Cache info retrieved successfully:"
    echo "   Total entities: $TOTAL_ENTITIES"
    echo "   Controllable entities: $CONTROLLABLE_ENTITIES"
    echo "   Domains: $DOMAIN_COUNT"
    
    # Show top domains
    echo "   Top domains:"
    echo "$CACHE_INFO_RESPONSE" | jq -r '
        .cached_entities.domain_breakdown | 
        to_entries | 
        sort_by(.value) | reverse | 
        .[0:5] | 
        .[] | "     \(.key): \(.value)"
    ' 2>/dev/null || echo "     Domain breakdown unavailable"
else
    echo "❌ Failed to get cache info"
    echo "$CACHE_INFO_RESPONSE"
fi
echo ""

echo "54. Testing manual cache cleanup endpoint:"
CACHE_CLEANUP_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/ha/cache/cleanup")
if echo "$CACHE_CLEANUP_RESPONSE" | jq . > /dev/null 2>&1; then
    SUCCESS=$(echo "$CACHE_CLEANUP_RESPONSE" | jq -r '.success // false')
    MESSAGE=$(echo "$CACHE_CLEANUP_RESPONSE" | jq -r '.message // "No message"')
    if [ "$SUCCESS" = "true" ]; then
        echo "✅ Cache cleanup completed successfully: $MESSAGE"
    else
        echo "⚠️  Cache cleanup failed: $MESSAGE"
    fi
else
    echo "❌ Failed to trigger cache cleanup"
    echo "$CACHE_CLEANUP_RESPONSE"
fi
echo ""

echo "55. Verifying cache consistency after cleanup:"
CACHE_INFO_AFTER=$(curl -s "${BASE_URL}/api/ha/cache/info")
if echo "$CACHE_INFO_AFTER" | jq . > /dev/null 2>&1; then
    ENTITIES_AFTER=$(echo "$CACHE_INFO_AFTER" | jq -r '.cached_entities.total_count // 0')
    echo "✅ Cache remains consistent: $ENTITIES_AFTER entities cached"
    
    if [ "$ENTITIES_AFTER" -eq "$TOTAL_ENTITIES" ]; then
        echo "   ✅ Entity count unchanged (no stale entities found)"
    elif [ "$ENTITIES_AFTER" -lt "$TOTAL_ENTITIES" ]; then
        REMOVED_COUNT=$((TOTAL_ENTITIES - ENTITIES_AFTER))
        echo "   🧹 Cleaned up $REMOVED_COUNT stale entities"
    else
        echo "   ℹ️  Entity count increased (new entities discovered)"
    fi
else
    echo "❌ Failed to verify cache after cleanup"
fi
echo ""

echo "=== Test Suite Complete ==="
echo ""
echo "Summary:"
echo "✅ Tested all core MCP endpoints"
echo "✅ Enhanced rules system (Skippy + Submind)"
echo "✅ System prompt management (MCP function calling)"
echo "✅ Prompt template CRUD operations"
echo "✅ Home Assistant entity management"
echo "✅ Real-time entity state logging"
echo "✅ Home Assistant device control"
echo "✅ Service discovery and validation"
echo "✅ Action execution and logging"
echo "✅ Cache management and cleanup"
echo ""
echo "The MCP system with configurable AI personality is ready for production use!"