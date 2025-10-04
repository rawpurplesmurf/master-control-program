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
