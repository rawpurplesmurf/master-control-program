# Example curl commands for testing the MCP API

## Enhanced Rules System

### Create a Skippy Guardrail Rule
```bash
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Garden lights daytime block",
    "rule_type": "skippy_guardrail",
    "description": "Prevent garden lights during daytime",
    "target_entity_pattern": "light.garden_*",
    "blocked_actions": ["turn_on"],
    "guard_conditions": {
      "time_after": "06:00",
      "time_before": "18:00"
    },
    "override_keywords": "emergency, force"
  }'
```

### Create a Submind Automation Rule
```bash
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "Welcome home lighting",
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
  }'
```

### List All Rules
```bash
curl http://localhost:8000/api/rules
```

### List Only Skippy Guardrail Rules
```bash
curl http://localhost:8000/api/rules?rule_type=skippy_guardrail
```

### List Only Submind Automation Rules
```bash
curl http://localhost:8000/api/rules?rule_type=submind_automation
```

### Get a Specific Rule
```bash
curl http://localhost:8000/api/rules/1
```

### Update a Rule (id=1)
```bash
curl -X PUT http://localhost:8000/api/rules/1 \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "is_active": false
  }'
```

### Execute a Submind Automation (id=2)
```bash
curl -X POST http://localhost:8000/api/rules/2/execute
```

### Delete a Rule (id=1)
```bash
curl -X DELETE http://localhost:8000/api/rules/1
```

## Command Processing Pipeline

### Basic Command Processing
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Turn on the living room light"
  }'
```

### Natural Language Device Query
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "What lights are currently on in my house?"
  }'
```

### Complex Home Automation Command
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "If it'\''s after sunset, turn on the porch light and set the living room to 30% brightness"
  }'
```

### Weather-Based Automation
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Check if it'\''s raining and close any open windows if so"
  }'
```

### Command with Source Tracking
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Good morning - start my morning routine",
    "source": "mobile_app"
  }'
```

### Example Response (Success)
The API will return a response like:
```json
{
  "response": "I've turned on the living room light for you.",
  "success": true,
  "template_used": "default",
  "data_fetchers_executed": ["current_time", "ha_device_status", "rules_list"],
  "processing_time_ms": 850,
  "context_keys": ["user_input", "current_time", "ha_device_status", "rules_list"]
}
```

### Example Response (Error)
If there's an issue, you might see:
```json
{
  "response": "Error: Prompt template 'default' not found. Please create a 'default' template first.",
  "success": false,
  "error": "template_not_found",
  "template_requested": "default",
  "processing_time_ms": 25
}
```
## Healthcheck Endpoints
### Check Home Assistant
```
curl http://localhost:8000/api/health/ha
```

### Check Redis
```
curl http://localhost:8000/api/health/redis
```

### Check Ollama
```
curl http://localhost:8000/api/health/ollama
```

### Check Database
```
curl http://localhost:8000/api/health/db
```

## Home Assistant Entities
### Get All HA Entities
```bash
curl http://localhost:8000/api/ha/entities
```

### Get HA Entities with Pretty JSON
```bash
curl -s http://localhost:8000/api/ha/entities | python -m json.tool
```

### Count Total Entities
```bash
curl -s http://localhost:8000/api/ha/entities | python -c "import sys, json; print(f'Total entities: {len(json.load(sys.stdin))}')"
```

### Get Entities by Domain
```bash
# Get only light entities
curl -s http://localhost:8000/api/ha/entities | python -c "
import sys, json
entities = json.load(sys.stdin)
lights = [e for e in entities if e['entity_id'].startswith('light.')]
print(f'Light entities: {len(lights)}')
for light in lights[:5]:  # Show first 5
    print(f'  {light[\"entity_id\"]}: {light[\"state\"]}')
"
```

## Prompt Templates
### Create a Prompt Template
```
curl -X POST http://localhost:8000/api/prompts \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Light Control Template",
    "intent_keywords": "light,lamp,brightness,illuminate",
    "system_prompt": "You are a home assistant controller that manages lighting systems.",
    "user_template": "Turn {action} the {entity} in the {location}",
    "pre_fetch_data": ["ha_device_status", "rules_list", "current_time", "light_entities"]
  }'
```

### List All Prompt Templates
```
curl http://localhost:8000/api/prompts
```

### Get a Specific Prompt Template (id=1)
```
curl http://localhost:8000/api/prompts/1
```

### Update a Prompt Template (id=1)
```
curl -X PUT http://localhost:8000/api/prompts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "Updated Light Control Template"
  }'
```

### Delete a Prompt Template (id=1)
```
curl -X DELETE http://localhost:8000/api/prompts/1
```

## System Prompts
### List All System Prompts
```bash
curl http://localhost:8000/api/system-prompts
```

### Get a Specific System Prompt (id=1)
```bash
curl http://localhost:8000/api/system-prompts/1
```

### Create a System Prompt
```bash
curl -X POST http://localhost:8000/api/system-prompts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Technical Assistant",
    "prompt": "You are a technical assistant specialized in home automation. Provide precise, technical responses with detailed explanations.",
    "description": "Technical expert persona for detailed automation assistance"
  }'
```

### Update a System Prompt (id=1)
```bash
curl -X PUT http://localhost:8000/api/system-prompts/1 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Technical Assistant",
    "prompt": "You are an advanced technical assistant with expertise in home automation systems."
  }'
```

### Delete a System Prompt (id=1)
```bash
curl -X DELETE http://localhost:8000/api/system-prompts/1
```

### Activate a System Prompt (id=2)
```bash
curl -X POST http://localhost:8000/api/system-prompts/2/activate
```

### Get Active System Prompt
```bash
curl http://localhost:8000/api/system-prompts/active
```

## Data Fetchers
### Create a Data Fetcher
```
curl -X POST http://localhost:8000/api/data-fetchers \
  -H "Content-Type: application/json" \
  -d '{
    "fetcher_key": "weather_data",
    "description": "Current weather information for home automation",
    "ttl_seconds": 600,
    "python_code": "import datetime\nresult = {\n    \"temperature\": 22.5,\n    \"humidity\": 65,\n    \"timestamp\": datetime.datetime.now().isoformat()\n}",
    "is_active": true
  }'
```

### List All Data Fetchers
```
curl http://localhost:8000/api/data-fetchers
```

### Get a Specific Data Fetcher
```
curl http://localhost:8000/api/data-fetchers/current_time
```

### Update a Data Fetcher
```
curl -X PUT http://localhost:8000/api/data-fetchers/current_time \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated current time fetcher with timezone",
    "ttl_seconds": 60
  }'
```

### Delete a Data Fetcher
```
curl -X DELETE http://localhost:8000/api/data-fetchers/weather_data
```

### Test a Data Fetcher (Execute without caching)
```
curl http://localhost:8000/api/data-fetchers/current_time/test
```

### Refresh a Data Fetcher (Force cache refresh)
```
curl -X POST http://localhost:8000/api/data-fetchers/current_time/refresh
```

## Prompt History

### Get Prompt History (All Interactions)
```bash
curl http://localhost:8000/api/prompt-history
```

### Get Prompt History with Pagination
```bash
curl "http://localhost:8000/api/prompt-history?limit=25&offset=50"
```

### Filter Prompt History by Source
```bash
# Get only API interactions
curl "http://localhost:8000/api/prompt-history?source=api"

# Get only Skippy interactions
curl "http://localhost:8000/api/prompt-history?source=skippy"

# Get only Submind interactions  
curl "http://localhost:8000/api/prompt-history?source=submind"

# Get only re-run interactions
curl "http://localhost:8000/api/prompt-history?source=rerun"
```

### Get Prompt History Statistics
```bash
curl http://localhost:8000/api/prompt-history/stats
```

### Get Specific Prompt Interaction
```bash
curl http://localhost:8000/api/prompt-history/1696345678000
```

### Re-run a Previous Prompt
```bash
curl -X POST http://localhost:8000/api/prompt-history/1696345678000/rerun
```

### Delete a Prompt Interaction
```bash
curl -X DELETE http://localhost:8000/api/prompt-history/1696345678000
```

### Example Response (Prompt History)
```json
[
  {
    "id": "1696345678000",
    "prompt": "System: You are a helpful home automation assistant.\n\nUser: Turn on the living room light",
    "response": "I'll turn on the living room light for you right away.",
    "source": "api",
    "timestamp": "2023-10-03T12:34:56+00:00",
    "metadata": {
      "template_used": "default",
      "processing_time_ms": 1250,
      "context_keys": ["user_input", "current_time", "ha_device_status"],
      "command": "Turn on the living room light"
    }
  }
]
```

### Example Response (Statistics)
```json
{
  "total_interactions": 1247,
  "source_distribution": {
    "api": 856,
    "skippy": 234,
    "submind": 89,
    "rerun": 45,
    "manual": 23
  },
  "recent_count": 100
}
```

### Example Response (Re-run)
```json
{
  "success": true,
  "new_interaction_id": "1696345678999",
  "original_interaction_id": "1696345678000", 
  "response": "I'll turn on the living room light for you right away.",
  "processing_time_ms": 890
}
```

---

## Home Assistant Entity Logging

### Get Entity State Change Log
```bash
# Get recent log entries for a specific entity
curl "http://localhost:8000/api/ha/entities/log/light.living_room"

# Get log entries with limit and date filtering
curl "http://localhost:8000/api/ha/entities/log/light.living_room?limit=50&start_date=2025-10-01T00:00:00Z&end_date=2025-10-03T23:59:59Z"

# Get logs for a switch entity
curl "http://localhost:8000/api/ha/entities/log/switch.kitchen_lights"
```

### Get Entity Log Summary Statistics
```bash
# Get 7-day summary (default)
curl "http://localhost:8000/api/ha/entities/log/light.living_room/summary"

# Get 14-day summary
curl "http://localhost:8000/api/ha/entities/log/light.living_room/summary?days=14"

# Get monthly summary (30 days max)
curl "http://localhost:8000/api/ha/entities/log/climate.main_thermostat/summary?days=30"
```

### Get All Logged Entities
```bash
# Get all entities with logged state changes
curl "http://localhost:8000/api/ha/entities/logs"

# Filter by domain - only light entities
curl "http://localhost:8000/api/ha/entities/logs?domain=light"

# Filter by domain - only switch entities  
curl "http://localhost:8000/api/ha/entities/logs?domain=switch"

# Filter by domain - only climate entities
curl "http://localhost:8000/api/ha/entities/logs?domain=climate"
```

### Example Entity Log Response
```json
{
  "entity_id": "light.living_room",
  "log_entries": [
    {
      "timestamp": "2025-10-03T15:30:45Z",
      "entity_id": "light.living_room",
      "old_state": {"state": "off", "attributes": {"brightness": null}},
      "new_state": {"state": "on", "attributes": {"brightness": 255}},
      "state_changed": true,
      "attributes_changed": true
    },
    {
      "timestamp": "2025-10-03T14:22:15Z",
      "entity_id": "light.living_room",
      "old_state": {"state": "on", "attributes": {"brightness": 180}},
      "new_state": {"state": "on", "attributes": {"brightness": 255}},
      "state_changed": false,
      "attributes_changed": true
    }
  ],
  "count": 2,
  "limit": 100,
  "start_date": null,
  "end_date": null
}
```

### Example Summary Response
```json
{
  "entity_id": "light.living_room",
  "total_changes": 24,
  "state_changes": 12,
  "attribute_changes": 18,
  "change_frequency_per_day": 3.4,
  "most_recent_change": {
    "timestamp": "2025-10-03T15:30:45Z",
    "entity_id": "light.living_room",
    "state_changed": true,
    "attributes_changed": true
  }
}
```

### Example All Logged Entities Response
```json
{
  "logged_entities": [
    "climate.main_thermostat",
    "light.kitchen",
    "light.living_room",
    "switch.porch_light"
  ],
  "count": 4,
  "domain_filter": null
}
```

---

## Home Assistant Device Control

### Get Available Services
```bash
# Get all services (cached)
curl http://localhost:8000/api/ha/services

# Force refresh from Home Assistant
curl http://localhost:8000/api/ha/services?refresh=true

# Get only light domain services
curl http://localhost:8000/api/ha/services?domain=light
```

### Execute Single Action
```bash
# Turn on a light with brightness
curl -X POST http://localhost:8000/api/ha/action \
  -H "Content-Type: application/json" \
  -d '{
    "service": "light.turn_on",
    "entity_id": "light.living_room",
    "data": {
      "brightness": 255,
      "color_name": "blue"
    }
  }'

# Turn off a switch
curl -X POST http://localhost:8000/api/ha/action \
  -H "Content-Type: application/json" \
  -d '{
    "service": "switch.turn_off",
    "entity_id": "switch.outlet"
  }'

# Set thermostat temperature
curl -X POST http://localhost:8000/api/ha/action \
  -H "Content-Type: application/json" \
  -d '{
    "service": "climate.set_temperature",
    "entity_id": "climate.thermostat",
    "data": {
      "temperature": 72
    }
  }'

# Service without entity (global action)
curl -X POST http://localhost:8000/api/ha/action \
  -H "Content-Type: application/json" \
  -d '{
    "service": "homeassistant.restart"
  }'
```

### Execute Bulk Actions
```bash
# Multiple actions in sequence (scene activation)
curl -X POST http://localhost:8000/api/ha/actions/bulk \
  -H "Content-Type: application/json" \
  -d '[
    {
      "service": "light.turn_on",
      "entity_id": "light.living_room",
      "data": {"brightness": 180}
    },
    {
      "service": "light.turn_on", 
      "entity_id": "light.kitchen",
      "data": {"brightness": 200}
    },
    {
      "service": "switch.turn_off",
      "entity_id": "switch.porch_light"
    },
    {
      "service": "climate.set_temperature",
      "entity_id": "climate.thermostat", 
      "data": {"temperature": 70}
    }
  ]'
```

### Get Action History
```bash
# Get recent actions for an entity
curl http://localhost:8000/api/ha/entities/light.living_room/actions

# Get limited number of actions
curl http://localhost:8000/api/ha/entities/light.living_room/actions?limit=10

# Get actions for a different entity type
curl http://localhost:8000/api/ha/entities/climate.thermostat/actions?limit=5
```

### Example Action Response
```json
{
  "success": true,
  "service": "light.turn_on",
  "entity_id": "light.living_room",
  "data": {
    "entity_id": "light.living_room",
    "brightness": 255,
    "color_name": "blue"
  },
  "ha_response": [],
  "service_info": {
    "service": "light.turn_on",
    "name": "turn_on",
    "description": "Turn the light on"
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Example Bulk Actions Response
```json
{
  "success": true,
  "total_actions": 4,
  "successful_actions": 4,
  "failed_actions": 0,
  "results": [
    {
      "action_index": 0,
      "action": {
        "service": "light.turn_on",
        "entity_id": "light.living_room"
      },
      "result": {
        "success": true,
        "service": "light.turn_on",
        "timestamp": "2023-01-01T12:00:00Z"
      }
    }
  ],
  "timestamp": "2023-01-01T12:00:00Z"
}
```

### Example Action History Response
```json
{
  "entity_id": "light.living_room",
  "actions": [
    {
      "timestamp": "2023-01-01T12:00:00Z",
      "action": {
        "service": "light.turn_on",
        "entity_id": "light.living_room",
        "data": {"brightness": 255}
      },
      "result": {
        "success": true,
        "ha_response": []
      },
      "old_state": {
        "state": "off",
        "attributes": {"brightness": 128}
      },
      "success": true
    },
    {
      "timestamp": "2023-01-01T11:30:00Z", 
      "action": {
        "service": "light.turn_off",
        "entity_id": "light.living_room"
      },
      "result": {
        "success": true,
        "ha_response": []
      },
      "old_state": {
        "state": "on",
        "attributes": {"brightness": 255}
      },
      "success": true
    }
  ],
  "count": 2,
  "limit": 50,
  "has_more": false
}
```
