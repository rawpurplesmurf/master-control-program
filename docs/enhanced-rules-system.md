# Enhanced Rules System Documentation

The Master Control Program now supports a comprehensive two-type rules system:

## Rule Types

### 1. Skippy Guardrails
**Purpose:** Contextual safety rules that prevent inappropriate actions
- **Type:** `skippy_guardrail`
- **Function:** Block specified actions on matching entities when guard conditions are met
- **Example:** Prevent garden lights from being turned on during daylight hours
- **Override:** Can be bypassed using specified keywords in commands

**Fields:**
- `target_entity_pattern`: Pattern to match entities (e.g., "light.garden_*")
- `blocked_actions`: Array of actions to block (e.g., ["turn_on", "turn_off"])
- `guard_conditions`: JSON object defining when rule applies (e.g., time ranges, sensor states)
- `override_keywords`: Comma-separated keywords that bypass the rule

### 2. Submind Automations
**Purpose:** Proactive automation rules that trigger actions based on conditions
- **Type:** `submind_automation`
- **Function:** Execute specified actions when trigger conditions are met
- **Example:** Turn on lights when arriving home after sunset
- **Execution:** Can be run manually or on schedule

**Fields:**
- `trigger_conditions`: JSON object defining when to execute (e.g., presence, time, sensors)
- `target_actions`: Array of Home Assistant service calls to execute
- `execution_schedule`: Optional cron-style schedule for automatic execution

## API Endpoints

### List Rules
```http
GET /api/rules
GET /api/rules?rule_type=skippy_guardrail
GET /api/rules?rule_type=submind_automation
```

### Get Specific Rule
```http
GET /api/rules/{rule_id}
```

### Create Rule
```http
POST /api/rules
Content-Type: application/json

{
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
}
```

### Update Rule
```http
PUT /api/rules/{rule_id}
Content-Type: application/json

{
  "description": "Updated description",
  "is_active": true
}
```

### Delete Rule
```http
DELETE /api/rules/{rule_id}
```

### Execute Submind Automation
```http
POST /api/rules/{rule_id}/execute
```

## Example Rules

### Skippy Guardrail Example
```json
{
  "rule_name": "No AC when windows open",
  "rule_type": "skippy_guardrail",
  "description": "Prevent air conditioning when windows are open",
  "target_entity_pattern": "climate.*",
  "blocked_actions": ["turn_on", "set_temperature"],
  "guard_conditions": {
    "sensor.window_contact": "open"
  },
  "override_keywords": "emergency, medical"
}
```

### Submind Automation Example
```json
{
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
    },
    {
      "service": "light.turn_on", 
      "entity_id": "light.hallway"
    }
  ]
}
```

## JSON Field Formats

### Guard Conditions & Trigger Conditions
```json
{
  "time_after": "sunset",
  "time_before": "23:00",
  "sensor.temperature": {"gt": 25},
  "person.john": "home",
  "binary_sensor.motion": "on"
}
```

### Target Actions
```json
[
  {
    "service": "light.turn_on",
    "entity_id": "light.living_room",
    "data": {
      "brightness": 180,
      "color_name": "warm_white"
    }
  },
  {
    "service": "climate.set_temperature",
    "entity_id": "climate.bedroom",
    "data": {
      "temperature": 22
    }
  }
]
```

## Admin Interface

The web admin interface at `/admin.html` provides:
- Separate forms for creating Skippy Guardrails and Submind Automations
- Rule filtering by type
- Visual status indicators (active/inactive)
- Manual execution for Submind Automations
- JSON field validation

## Database Schema

The enhanced rules table supports:
- Both rule types in a single table with type discrimination
- JSON storage for complex condition and action structures
- Priority system for rule ordering
- Execution tracking with timestamps and counters
- Proper indexing for performance

## Integration

Rules integrate with:
- **Ollama Processing:** Skippy Guardrails check commands before execution
- **Home Assistant:** Target actions execute HA services
- **Data Fetchers:** Conditions can reference fetched data
- **Health Monitoring:** Rule execution status tracked
- **Caching:** Rule evaluations cached for performance