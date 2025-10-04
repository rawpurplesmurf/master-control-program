
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

### 4. `/api/data-fetchers` - Data Fetcher Management

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

````
