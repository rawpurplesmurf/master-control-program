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

## Create a Command
```
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -d '{
    "command": "Turn on the living room light"
  }'
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
