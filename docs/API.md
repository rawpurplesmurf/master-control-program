
# Master Control Program API

This document outlines the API for the Master Control Program (MCP). The API is used to send natural language commands and manage rules for the MCP.

## Endpoints

### 1. `/api/command`

* **Method:** `POST`
* **Description:** Processes a natural language command and executes the corresponding actions.

#### Request Body

The request body should be a JSON object with a single key, `command`.

* `command` (string, required): The natural language command to be processed.

**Example:**

```json
{
  "command": "Turn on the living room light"
}
```

#### Responses

**200 OK - Success**

Indicates that the command was successfully processed and executed.

* `status` (string): Always "success" on success.
* `message` (string): A success message.
* `executed_actions` (array): A list of the actions that were executed.

**Example:**

```json
{
  "status": "success",
  "message": "Command executed successfully.",
  "executed_actions": [
    {
      "service": "turn_on",
      "entity_id": "light.living_room",
      "data": {}
    }
  ]
}
```

**400 Bad Request - Error**

Indicates that there was an error processing the command. This can be due to an invalid request format or an error from the Ollama service.

* `status` (string): Always "error" on error.
* `message` (string): A description of the error.

**Example:**

```json
{
  "status": "error",
  "message": "Ollama returned an invalid JSON response."
}
```

**500 Internal Server Error - Error**

Indicates that an unexpected error occurred on the server.

* `status` (string): Always "error" on error.
* `message` (string): A generic error message.

**Example:**

```json
{
  "status": "error",
  "message": "An internal error occurred."
}
```

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

````
