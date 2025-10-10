
# Master Control Program API

This document outlines the API for the Master Control Program (MCP). The API is used to send natural language commands and manage rules for the MCP.

## Endpoints

### 1. `/api/command` - Enhanced Command Processing Pipeline

* **Method:** `POST`
* **Description:** Processes a natural language command through the complete MCP pipeline using prompt templates and data fetchers.

#### How It Works

The command processing pipeline:
1. **Template Selection**: Determines which prompt template to use (currently hardcoded to 'default')
2. **Data Fetching**: Executes all data fetchers required by the selected template
3. **Prompt Construction**: Builds the system and user prompts with fetched data
4. **LLM Processing**: Sends the constructed prompt to the Ollama LLM
5. **Response Generation**: Returns the LLM response with processing metadata

#### Request Body

* `command` (string, required): The natural language command to be processed
* `source` (string, optional): Source of the command (defaults to "api")

**Example:**

```json
{
  "command": "What lights are currently on in my house?"
}
```

#### Responses

**200 OK - Success**

Returns the processed command response with metadata.

**Success Response:**
```json
{
  "response": "Based on the current device status, you have 3 lights that are currently on: the living room light, kitchen light, and bedroom lamp. The porch light and bathroom light are currently off.",
  "template_used": "default",
  "data_fetchers_executed": ["current_time", "ha_device_status", "rules_list"],
  "processing_time_ms": 1250,
  "context_keys": ["user_input", "current_time", "ha_device_status", "rules_list"],
  "success": true
}
```

**Error Response (Template Not Found):**
```json
{
  "response": "Error: Prompt template 'default' not found. Please create a 'default' template first.",
  "error": "template_not_found",
  "template_requested": "default",
  "processing_time_ms": 45,
  "success": false
}
```

**Error Response (Processing Error):**
```json
{
  "response": "I apologize, but I encountered an error processing your command: Connection to Ollama failed",
  "error": "processing_error",
  "error_details": "Connection to Ollama failed",
  "processing_time_ms": 500,
  "success": false
}
```

#### Response Fields

* `response` (string): The LLM-generated response or error message
* `success` (boolean): Whether the command was processed successfully
* `template_used` (string): Name of the prompt template that was used
* `data_fetchers_executed` (array): List of data fetcher keys that were executed
* `processing_time_ms` (integer): Total processing time in milliseconds
* `context_keys` (array): Keys available in the prompt context
* `error` (string, optional): Error type identifier when success is false
* `error_details` (string, optional): Detailed error information for debugging

#### Prerequisites

For the command endpoint to work properly:
1. A prompt template named 'default' must exist in the database
2. All data fetchers referenced in the template's `pre_fetch_data` must be configured
3. The Ollama LLM service must be running and accessible

---

### 2. `/api/rules` - Enhanced Rules System

The MCP supports two types of rules:
- **Skippy Guardrails**: Contextual safety rules that prevent inappropriate actions
- **Submind Automations**: Proactive automation rules that trigger actions

#### List All Rules

* **Method:** `GET`
* **Query Parameters:**
  * `rule_type` (optional): Filter by `skippy_guardrail` or `submind_automation`
* **Response:** Array of rule objects.

**Example:**

```json
[
  {
    "id": 1,
    "rule_name": "Garden lights daytime block",
    "rule_type": "skippy_guardrail",
    "description": "Prevent garden lights during daytime",
    "is_active": true,
    "priority": 0,
    "target_entity_pattern": "light.garden_*",
    "blocked_actions": ["turn_on"],
    "guard_conditions": {"time_after": "06:00", "time_before": "18:00"},
    "override_keywords": "emergency, force"
  },
  {
    "id": 2,
    "rule_name": "Welcome home lighting",
    "rule_type": "submind_automation", 
    "description": "Turn on lights when arriving home after dark",
    "is_active": true,
    "priority": 0,
    "trigger_conditions": {"person.john": "home", "sun.sun": "below_horizon"},
    "target_actions": [{"service": "light.turn_on", "entity_id": "light.living_room"}]
  }
]
```

#### Get Specific Rule

* **Method:** `GET`
* **Path:** `/api/rules/{rule_id}`
* **Response:** Single rule object with all fields.

#### Create a Skippy Guardrail

* **Method:** `POST`
* **Request Body:**

```json
{
  "rule_name": "No AC when windows open",
  "rule_type": "skippy_guardrail",
  "description": "Prevent air conditioning when windows are open",
  "target_entity_pattern": "climate.*",
  "blocked_actions": ["turn_on", "set_temperature"],
  "guard_conditions": {"sensor.window_contact": "open"},
  "override_keywords": "emergency, medical"
}
```

#### Create a Submind Automation

* **Method:** `POST`
* **Request Body:**

```json
{
  "rule_name": "Evening arrival automation",
  "rule_type": "submind_automation",
  "description": "Activate evening scene when arriving home",
  "trigger_conditions": {
    "person.john": "home",
    "time_after": "17:00"
  },
  "target_actions": [
    {
      "service": "scene.turn_on",
      "entity_id": "scene.evening_arrival"
    }
  ],
  "execution_schedule": "*/5 * * * *"
}
```

#### Update a Rule

* **Method:** `PUT`
* **Path:** `/api/rules/{rule_id}`
* **Request Body:** Any subset of rule fields to update.

```json
{
  "description": "Updated description",
  "is_active": false
}
```

* **Response:** The updated rule object.

#### Delete a Rule

* **Method:** `DELETE`
* **Path:** `/api/rules/{rule_id}`
* **Response:**

```json
{
  "detail": "Rule deleted"
}
```

#### Execute Submind Automation

* **Method:** `POST`
* **Path:** `/api/rules/{rule_id}/execute`
* **Description:** Manually execute a submind automation rule
* **Response:**

```json
{
  "message": "Rule 'Evening arrival automation' executed successfully",
  "actions_executed": 1
}
```

---

### 3. `/api/prompts` - Prompt Templates

Prompt templates define structured templates for generating prompts with specific intents and data requirements.

**Field Details:**
- `template_name`: Unique name for the template
- `intent_keywords`: Comma-separated keywords that trigger this template  
- `system_prompt`: System instructions for the LLM
- `user_template`: Template string with placeholders like `{entity}`, `{action}`
- `pre_fetch_data`: Array of strings specifying what data to fetch (e.g., `["ha_device_status", "rules_list", "current_time"]`)

#### List All Prompt Templates

* **Method:** `GET`
* **Response:** Array of prompt template objects.

**Example:**

```json
[
  {
    "id": 1,
    "template_name": "Light Control",
    "intent_keywords": "light,lamp,brightness",
    "system_prompt": "You are a home assistant controller...",
    "user_template": "Turn {action} the {entity}",
    "pre_fetch_data": ["ha_device_status", "rules_list", "current_time"],
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-10-01T10:00:00Z"
  }
]
```

#### Create a Prompt Template

* **Method:** `POST`
* **Request Body:**

```json
{
  "template_name": "Light Control",
  "intent_keywords": "light,lamp,brightness",
  "system_prompt": "You are a home assistant controller...",
  "user_template": "Turn {action} the {entity}",
  "pre_fetch_data": ["ha_device_status", "rules_list", "current_time"]
}
```

* **Response:** The created prompt template object (201 Created).

#### Get a Prompt Template

* **Method:** `GET`
* **Path:** `/api/prompts/{template_id}`
* **Response:** The prompt template object.

#### Update a Prompt Template

* **Method:** `PUT`
* **Path:** `/api/prompts/{template_id}`
* **Request Body:** Any subset of template fields to update.

```json
{
  "template_name": "Updated Light Control"
}
```

* **Response:** The updated prompt template object.

#### Delete a Prompt Template

* **Method:** `DELETE`
* **Path:** `/api/prompts/{template_id}`
* **Response:** 204 No Content

---

### 4. `/api/system-prompts` - System Prompt Management

System prompts define the core behavior and personality of the LLM for different interaction modes. They support MCP function calling and can be dynamically switched through the admin interface.

#### List All System Prompts

* **Method:** `GET`
* **Path:** `/api/system-prompts`

**Response:**
```json
[
  {
    "id": 1,
    "name": "default_mcp",
    "prompt": "You are a Home Assistant controller. You can either:\n1. Answer questions directly with natural language\n2. Execute actions using the provided functions\n\nFor direct questions, respond naturally.\nFor action requests, use the appropriate function calls.\n\nAvailable functions will be provided in the context.",
    "description": "Default MCP system prompt with function calling capabilities",
    "is_active": true,
    "created_at": "2025-10-09T18:00:00Z",
    "updated_at": "2025-10-09T18:00:00Z"
  }
]
```

#### Get Active System Prompt

* **Method:** `GET`
* **Path:** `/api/system-prompts/active`

**Response:**
```json
{
  "id": 1,
  "name": "default_mcp",
  "prompt": "You are a Home Assistant controller...",
  "description": "Default MCP system prompt with function calling capabilities",
  "is_active": true
}
```

#### Create System Prompt

* **Method:** `POST`
* **Path:** `/api/system-prompts`

**Request Body:**
```json
{
  "name": "custom_assistant",
  "prompt": "You are a helpful Home Assistant controller with a friendly personality. Always greet users warmly and explain your actions clearly.",
  "description": "Custom friendly assistant system prompt",
  "is_active": false
}
```

**Response:**
```json
{
  "id": 6,
  "name": "custom_assistant",
  "prompt": "You are a helpful Home Assistant controller...",
  "description": "Custom friendly assistant system prompt",
  "is_active": false,
  "message": "System prompt created successfully"
}
```

#### Update System Prompt

* **Method:** `PUT`
* **Path:** `/api/system-prompts/{prompt_id}`

**Request Body:**
```json
{
  "description": "Updated description",
  "is_active": true
}
```

**Response:**
```json
{
  "id": 6,
  "name": "custom_assistant",
  "prompt": "You are a helpful Home Assistant controller...",
  "description": "Updated description", 
  "is_active": true,
  "message": "System prompt updated successfully"
}
```

#### Activate System Prompt

* **Method:** `POST`
* **Path:** `/api/system-prompts/{prompt_id}/activate`

**Response:**
```json
{
  "message": "System prompt 'custom_assistant' is now active",
  "active_prompt": {
    "id": 6,
    "name": "custom_assistant",
    "description": "Updated description"
  }
}
```

#### Delete System Prompt

* **Method:** `DELETE`
* **Path:** `/api/system-prompts/{prompt_id}`

**Response:**
```json
{
  "message": "System prompt 'custom_assistant' deleted successfully"
}
```

---

### 5. `/api/data-fetchers` - Data Fetcher Management

Data fetchers are configurable Python code blocks that retrieve specific data for prompt templates. Each fetcher has a unique key, description, TTL for caching, and Python code that executes safely.

**Field Details:**
- `fetcher_key`: Unique identifier for the data fetcher (used in prompt template `pre_fetch_data`)
- `description`: Human-readable description of what the fetcher does
- `ttl_seconds`: Cache time-to-live in seconds (default: 300)
- `python_code`: Python code that sets a `result` variable with the fetched data
- `is_active`: Whether the fetcher is enabled

#### List All Data Fetchers

* **Method:** `GET`
* **Response:** Array of data fetcher objects.

**Example:**

```json
[
  {
    "id": 1,
    "fetcher_key": "current_time",
    "description": "Current timestamp and date information",
    "ttl_seconds": 300,
    "python_code": "import datetime\nresult = {\n    \"current_time\": datetime.datetime.now().isoformat()\n}",
    "is_active": true,
    "created_at": "2025-10-01T10:00:00Z",
    "updated_at": "2025-10-01T10:00:00Z"
  }
]
```

#### Create a Data Fetcher

* **Method:** `POST`
* **Request Body:**

```json
{
  "fetcher_key": "weather_data",
  "description": "Current weather information",
  "ttl_seconds": 600,
  "python_code": "import datetime\nresult = {\n    \"temperature\": 22.5,\n    \"timestamp\": datetime.datetime.now().isoformat()\n}",
  "is_active": true
}
```

* **Response:** The created data fetcher object (201 Created).

#### Get a Data Fetcher

* **Method:** `GET`
* **Path:** `/api/data-fetchers/{fetcher_key}`
* **Response:** The data fetcher object.

#### Update a Data Fetcher

* **Method:** `PUT`
* **Path:** `/api/data-fetchers/{fetcher_key}`
* **Request Body:** Any subset of data fetcher fields to update.

#### Delete a Data Fetcher

* **Method:** `DELETE`
* **Path:** `/api/data-fetchers/{fetcher_key}`
* **Response:** 204 No Content

#### Test a Data Fetcher

* **Method:** `GET`
* **Path:** `/api/data-fetchers/{fetcher_key}/test`
* **Response:** The result of executing the fetcher code without caching.

**Example:**

```json
{
  "fetcher_key": "current_time",
  "result": {
    "current_time": "2025-10-01T15:30:00.123456",
    "unix_timestamp": 1727795400
  },
  "tested_at": "2025-10-01T15:30:00.123456"
}
```

#### Refresh a Data Fetcher

* **Method:** `POST`
* **Path:** `/api/data-fetchers/{fetcher_key}/refresh`
* **Response:** The result of executing the fetcher and updating the cache.

---

### 5. Health Check Endpoints

These endpoints allow you to check the health status of various system components.

#### Check Database Health

* **Method:** `GET`
* **Path:** `/api/health/db`
* **Response:**

```json
{
  "status": "ok"
}
```

Or on error:

```json
{
  "status": "error",
  "detail": "Connection failed"
}
```

#### Check Redis Health

* **Method:** `GET`
* **Path:** `/api/health/redis`
* **Response:** Same format as database health check.

#### Check Home Assistant Health

* **Method:** `GET`
* **Path:** `/api/health/ha`
* **Response:** Same format as database health check.

Alternative endpoint:
* **Path:** `/api/health/homeassistant` (alias for `/api/health/ha`)

#### Check Ollama Health

* **Method:** `GET`
* **Path:** `/api/health/ollama`
* **Response:** Same format as database health check.

---

### 6. Home Assistant Entities

#### Get All HA Entities

* **Method:** `GET`
* **Path:** `/api/ha/entities`
* **Description:** Retrieves all Home Assistant entities from Redis cache or directly from HA API if cache is empty.

**Response:** Array of entity objects with full state information.

**Example:**

```json
[
  {
    "entity_id": "light.living_room",
    "state": "on",
    "attributes": {
      "friendly_name": "Living Room Light",
      "brightness": 255,
      "color_mode": "brightness",
      "supported_features": 4,
      "supported_color_modes": ["brightness"]
    },
    "last_changed": "2025-10-03T12:34:56.789Z",
    "last_updated": "2025-10-03T12:34:56.789Z"
  },
  {
    "entity_id": "switch.kitchen_fan",
    "state": "off",
    "attributes": {
      "friendly_name": "Kitchen Fan",
      "device_class": "switch"
    },
    "last_changed": "2025-10-03T10:15:30.123Z",
    "last_updated": "2025-10-03T10:15:30.123Z"
  }
]
```

**Error Responses:**

* **503 Service Unavailable** - Redis or Home Assistant connection error
* **500 Internal Server Error** - Unexpected error fetching entities

## 8. `/api/prompt-history` - Prompt History Management

### GET `/api/prompt-history`
* **Method:** `GET`
* **Description:** Retrieve prompt history with optional filtering and pagination.

#### Query Parameters
* `limit` (integer, optional): Maximum number of interactions to return (default: 100)
* `offset` (integer, optional): Number of interactions to skip for pagination (default: 0)  
* `source` (string, optional): Filter by source (api, skippy, submind, rerun, manual)

#### Response
Returns an array of prompt interaction objects:

```json
[
  {
    "id": "1696345678000",
    "prompt": "System: You are helpful\nUser: What time is it?", 
    "response": "The current time is 2:30 PM EST.",
    "source": "api",
    "timestamp": "2023-10-03T12:34:56+00:00",
    "metadata": {
      "template_used": "default",
      "processing_time_ms": 1250,
      "context_keys": ["user_input", "current_time"],
      "command": "What time is it?"
    }
  }
]
```

### GET `/api/prompt-history/stats`
* **Method:** `GET`
* **Description:** Get statistics about prompt history.

#### Response
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

### GET `/api/prompt-history/{interaction_id}`
* **Method:** `GET`
* **Description:** Get a specific prompt interaction by ID.

#### Response
Returns a single prompt interaction object (same structure as array item above).

**Error Responses:**
* **404 Not Found** - Interaction ID not found

### POST `/api/prompt-history/{interaction_id}/rerun`
* **Method:** `POST`
* **Description:** Re-run a previous prompt interaction with the same prompt.

#### Response
```json
{
  "success": true,
  "new_interaction_id": "1696345678999", 
  "original_interaction_id": "1696345678000",
  "response": "The current time is 3:45 PM EST.",
  "processing_time_ms": 890
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Original interaction not found"
}
```

### DELETE `/api/prompt-history/{interaction_id}`
* **Method:** `DELETE`
* **Description:** Delete a specific prompt interaction from history.

#### Response
```json
{
  "message": "Prompt interaction 1696345678000 deleted successfully"
}
```

**Error Responses:**
* **404 Not Found** - Interaction ID not found
* **500 Internal Server Error** - Error deleting interaction

## How Prompt History Works

The prompt history system automatically captures all LLM interactions:

1. **Automatic Storage**: Every command processed through `/api/command` is stored
2. **Source Tracking**: Commands are tagged with their source (api, skippy, submind, etc.)
3. **Complete Context**: Both the full prompt sent to the LLM and response received are stored
4. **Metadata Capture**: Processing time, template used, context keys, and other metadata
5. **Redis Storage**: All history is stored in Redis with 30-day retention
6. **Re-execution**: Any previous prompt can be re-run to see how the LLM responds now

### Use Cases

* **Debugging**: See exactly what prompts were sent to the LLM
* **Performance Analysis**: Track processing times and template usage  
* **Response Comparison**: Re-run old prompts to see how responses change
* **Audit Trail**: Complete history of all AI interactions
* **Template Testing**: Compare responses across different prompt templates

---

## Home Assistant Entity Log Endpoints

The entity logging system provides detailed tracking of Home Assistant entity state changes with real-time WebSocket integration and 7-day retention.

### 1. `/api/ha/entities/log/{entity_id}` - Get Entity Change Log

* **Method:** `GET`
* **Description:** Retrieves chronological log of state changes for a specific Home Assistant entity.

#### Parameters

* `entity_id` (path, required): The Home Assistant entity ID (e.g., "light.living_room")
* `limit` (query, optional): Maximum number of log entries to return (1-1000, default: 100)
* `start_date` (query, optional): Start date in ISO format (e.g., "2025-10-01T00:00:00Z")
* `end_date` (query, optional): End date in ISO format (e.g., "2025-10-03T23:59:59Z")

#### Example Request
```bash
GET /api/ha/entities/log/light.living_room?limit=50&start_date=2025-10-01T00:00:00Z
```

#### Response
```json
{
  "entity_id": "light.living_room",
  "log_entries": [
    {
      "timestamp": "2025-10-03T12:00:00Z",
      "entity_id": "light.living_room",
      "old_state": {"state": "off", "attributes": {"brightness": null}},
      "new_state": {"state": "on", "attributes": {"brightness": 255}},
      "state_changed": true,
      "attributes_changed": true
    },
    {
      "timestamp": "2025-10-03T11:30:00Z",
      "entity_id": "light.living_room", 
      "old_state": {"state": "on", "attributes": {"brightness": 255}},
      "new_state": {"state": "off", "attributes": {"brightness": null}},
      "state_changed": true,
      "attributes_changed": true
    }
  ],
  "count": 2,
  "limit": 50,
  "start_date": "2025-10-01T00:00:00Z",
  "end_date": null
}
```

**Error Responses:**
* **500 Internal Server Error** - Error retrieving entity log

---

### 2. `/api/ha/entities/log/{entity_id}/summary` - Get Entity Log Summary

* **Method:** `GET`
* **Description:** Provides statistical summary of entity state changes over a specified period.

#### Parameters

* `entity_id` (path, required): The Home Assistant entity ID
* `days` (query, optional): Number of days to analyze (1-30, default: 7)

#### Example Request
```bash
GET /api/ha/entities/log/light.living_room/summary?days=14
```

#### Response
```json
{
  "entity_id": "light.living_room",
  "total_changes": 45,
  "state_changes": 22,
  "attribute_changes": 38,
  "change_frequency_per_day": 3.2,
  "most_recent_change": {
    "timestamp": "2025-10-03T12:00:00Z",
    "entity_id": "light.living_room",
    "state_changed": true,
    "attributes_changed": true
  }
}
```

**Error Responses:**
* **422 Unprocessable Entity** - Invalid days parameter
* **500 Internal Server Error** - Error generating summary

---

### 3. `/api/ha/entities/logs` - Get All Logged Entities

* **Method:** `GET`
* **Description:** Returns list of all Home Assistant entities that have logged state changes.

#### Parameters

* `domain` (query, optional): Filter by entity domain (e.g., "light", "switch", "climate")

#### Example Request
```bash
GET /api/ha/entities/logs?domain=light
```

#### Response
```json
{
  "logged_entities": [
    "light.living_room",
    "light.kitchen", 
    "light.bedroom",
    "light.porch"
  ],
  "count": 4,
  "domain_filter": "light"
}
```

**Error Responses:**
* **500 Internal Server Error** - Error retrieving logged entities

---

## Home Assistant Device Control API

### 1. `/api/ha/services` - Get Available Services

* **Method:** `GET`  
* **Description:** Returns all available Home Assistant services with real-time data from the Home Assistant `/api/services` endpoint.

#### Parameters

* `refresh` (query, optional): Force refresh from Home Assistant (bypasses cache)
* `domain` (query, optional): Filter services by specific domain (e.g., "light", "switch")

#### Example Requests
```bash
# Get all services (cached)
GET /api/ha/services

# Force refresh from Home Assistant
GET /api/ha/services?refresh=true

# Get only light domain services
GET /api/ha/services?domain=light
```

#### Response
```json
{
  "services": {
    "light": [
      {
        "service": "light.turn_on",
        "name": "turn_on",
        "description": "Turn the light on",
        "fields": [
          {
            "name": "brightness",
            "description": "Brightness level (0-255)",
            "required": false,
            "selector": {"number": {"min": 0, "max": 255}}
          },
          {
            "name": "color_name", 
            "description": "Color name",
            "required": false,
            "example": "red"
          }
        ],
        "parameters": ["brightness", "color_name"]
      },
      {
        "service": "light.turn_off",
        "name": "turn_off", 
        "description": "Turn the light off",
        "fields": [],
        "parameters": []
      }
    ],
    "switch": [
      {
        "service": "switch.turn_on",
        "name": "turn_on",
        "description": "Turn the switch on", 
        "fields": [],
        "parameters": []
      }
    ]
  },
  "total_services": 3,
  "total_domains": 2,
  "last_updated": "2023-01-01T12:00:00Z",
  "cached": true
}
```

**Error Responses:**
* **500 Internal Server Error** - Error retrieving services

---

### 2. `/api/ha/action` - Execute Home Assistant Action

* **Method:** `POST`
* **Description:** Execute an action on a Home Assistant device with validation and logging.

#### Request Body

```json
{
  "service": "light.turn_on",
  "entity_id": "light.living_room", 
  "data": {
    "brightness": 255,
    "color_name": "blue"
  }
}
```

#### Response

**Success Response:**
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
    "description": "Turn on light"
  },
  "timestamp": "2023-01-01T12:00:00Z"
}
```

**Failure Response:**
```json
{
  "success": false,
  "error": "Entity light.nonexistent not found or not available",
  "service": "light.turn_on",
  "entity_id": "light.nonexistent"
}
```

**Error Responses:**
* **500 Internal Server Error** - Error executing action

---

### 3. `/api/ha/actions/bulk` - Execute Multiple Actions

* **Method:** `POST`
* **Description:** Execute multiple Home Assistant actions in sequence. Useful for scenes and automation sequences.

#### Request Body

```json
[
  {
    "service": "light.turn_on",
    "entity_id": "light.living_room",
    "data": {"brightness": 255}
  },
  {
    "service": "switch.turn_off", 
    "entity_id": "switch.outlet"
  },
  {
    "service": "climate.set_temperature",
    "entity_id": "climate.thermostat",
    "data": {"temperature": 72}
  }
]
```

#### Response

```json
{
  "success": true,
  "total_actions": 3,
  "successful_actions": 3,
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
        "service": "light.turn_on"
      }
    }
  ],
  "timestamp": "2023-01-01T12:00:00Z"
}
```

**Error Responses:**
* **400 Bad Request** - Too many actions (max 50)
* **500 Internal Server Error** - Error executing actions

---

### 4. `/api/ha/entities/{entity_id}/actions` - Get Action History

* **Method:** `GET`
* **Description:** Get execution history for a specific entity with 7-day retention.

#### Parameters

* `entity_id` (path, required): The Home Assistant entity ID
* `limit` (query, optional): Maximum actions to return (1-200, default: 50)

#### Example Request
```bash
GET /api/ha/entities/light.living_room/actions?limit=10
```

#### Response
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
    }
  ],
  "count": 1,
  "limit": 10,
  "has_more": false
}
```

**Error Responses:**
* **422 Unprocessable Entity** - Invalid limit parameter
* **500 Internal Server Error** - Error getting action history

---

### 6. `/api/ha/cache/cleanup` - Manual Cache Cleanup

* **Method:** `POST`
* **Description:** Manually trigger cleanup of stale Home Assistant entities from Redis cache.

Compares cached entities with current Home Assistant state and removes any entities that no longer exist in HA. This is normally done automatically every hour by the WebSocket client.

#### Request Body
None required.

#### Example Request
```bash
POST /api/ha/cache/cleanup
```

#### Response
```json
{
  "success": true,
  "message": "Cache cleanup completed successfully",
  "timestamp": "2025-10-10T01:46:19.611634Z"
}
```

**Error Responses:**
* **503 Service Unavailable** - WebSocket client not available
* **500 Internal Server Error** - Error during cleanup

---

### 7. `/api/ha/cache/info` - Cache Information

* **Method:** `GET`
* **Description:** Get information about the current Home Assistant cache state.

Returns statistics about cached entities, domains, and cache metadata for monitoring and debugging cache consistency.

#### Example Request
```bash
GET /api/ha/cache/info
```

#### Response
```json
{
  "cache_metadata": {
    "last_update": "2025-10-10T01:46:01.041168",
    "total_entities": 333,
    "controllable_entities": 179,
    "domains": ["light", "switch", "sensor", "binary_sensor", ...]
  },
  "cached_entities": {
    "total_count": 333,
    "domain_breakdown": {
      "sensor": 60,
      "switch": 125,
      "light": 39,
      ...
    },
    "controllable_count": 179
  },
  "cache_keys": {
    "entity_keys_sample": ["ha:entity:light.living_room", ...],
    "total_entity_keys": 333
  },
  "timestamp": "2025-10-10T01:46:14.315286Z"
}
```

**Error Responses:**
* **503 Service Unavailable** - Redis client not available
* **500 Internal Server Error** - Error getting cache info

---

## Device Control Features

The Home Assistant device control system provides:

* **Live Service Discovery**: Real-time fetching from Home Assistant's `/api/services` endpoint
* **Redis Caching**: 5-minute cache for performance with force refresh capability
* **Service Validation**: Validates services exist before execution
* **Entity Validation**: Checks entity exists and is controllable
* **Action Logging**: 7-day retention of all action executions with Redis storage
* **Bulk Operations**: Execute multiple actions in sequence for scenes/automation
* **Comprehensive Error Handling**: Detailed error responses with suggestions
* **Field-Aware Execution**: Supports all Home Assistant service parameters and selectors

---

## Cache Management Features

The cache management system ensures consistency between Redis cache and Home Assistant state:

* **Real-time Entity Removal**: WebSocket events automatically remove deleted entities from cache
* **Periodic Cleanup**: Hourly background process removes stale cache entries 
* **Manual Cleanup**: API endpoint allows triggering cleanup on demand
* **Removal Logging**: All entity removals are logged with 7-day retention
* **Cache Consistency**: Domain and controllable entity caches updated during cleanup
* **Stale Detection**: Compares cached entities with current Home Assistant state
* **Error Handling**: Robust error handling with detailed logging for troubleshooting

### Entity Removal Process

When an entity is removed from Home Assistant:

1. **WebSocket Event**: HA sends state change with `new_state=None`
2. **Cache Deletion**: Entity removed from `ha:entity:{entity_id}` key
3. **Logging**: Removal logged to `ha:log:{entity_id}` with `entity_removed: true`
4. **Domain Refresh**: Domain cache (`ha:domain:{domain}`) refreshed to remove entity
5. **Controllable Refresh**: Controllable entities cache updated if applicable

### Periodic Cleanup

Every hour, the system:

1. **Fetch Current State**: Gets all entities from Home Assistant `/api/states`
2. **Compare Caches**: Scans Redis for `ha:entity:*` keys
3. **Identify Stale**: Finds cached entities not in current HA state
4. **Remove Stale**: Deletes stale cache entries and logs removals
5. **Refresh Caches**: Updates domain and controllable entity caches

---

## Entity Logging Features

The entity logging system provides:

* **Real-time Tracking**: WebSocket connection captures all state changes immediately
* **7-day Retention**: Automatic cleanup of logs older than 7 days
* **State & Attribute Changes**: Tracks both state transitions and attribute modifications
* **Redis Storage**: High-performance storage with sorted sets for chronological access
* **Domain Filtering**: Filter entities by Home Assistant domain
* **Statistical Analysis**: Summary statistics for change frequency analysis
* **Date Range Queries**: Query logs within specific time periods

````
