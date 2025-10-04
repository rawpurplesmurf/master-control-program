# Data Fetcher System

The Data Fetcher System is a powerful, configurable component of the Master Control Program (MCP) that enables dynamic data retrieval for prompt templates. It allows you to execute Python code blocks safely to fetch data from various sources, with built-in caching and error handling.

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Creating Data Fetchers](#creating-data-fetchers)
- [Common Use Cases](#common-use-cases)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

Data fetchers are configurable Python code blocks stored in the database that can:

- Retrieve data from Redis cache (Home Assistant entities, etc.)
- Query the MCP database (rules, templates, etc.)
- Generate computed values (timestamps, calculations, etc.)
- Transform and filter data for prompt templates
- Cache results with configurable TTL (Time To Live)

### Key Features

- **Safe Execution**: Restricted Python environment with controlled imports
- **Redis Caching**: Automatic caching with configurable TTL per fetcher
- **Error Handling**: Graceful error handling with `failed_fetch` flags
- **Real-time Testing**: Test endpoints for immediate feedback
- **Web Management**: Full CRUD operations via admin interface

## How It Works

### 1. **Storage**
Data fetchers are stored in the `data_fetchers` MySQL table with:
- `fetcher_key`: Unique identifier used in prompt templates
- `description`: Human-readable description
- `ttl_seconds`: Cache duration (default: 300 seconds)
- `python_code`: The executable Python code
- `is_active`: Enable/disable flag

### 2. **Execution Flow**
```
1. Prompt template specifies required data in pre_fetch_data array
2. For each fetcher_key in the array:
   a. Check Redis cache (mcp:prefetch:{fetcher_key})
   b. If cached and fresh (< TTL), return cached data
   c. If not cached or stale, execute Python code
   d. Cache the result with timestamp
   e. Return the data
3. All fetched data is available as template variables
```

### 3. **Caching Strategy**
- **Redis Key**: `mcp:prefetch:{fetcher_key}`
- **Freshness Check**: Data is considered fresh if age < `ttl_seconds`
- **Cache Entry**: Includes data, timestamp, and metadata
- **TTL**: Each fetcher can have its own cache duration

## Architecture

### Safe Execution Environment

The Python execution environment includes these safe built-ins:
```python
{
    '__builtins__': {
        '__import__': __import__,  # For import statements
        'len': len, 'list': list, 'dict': dict, 'str': str,
        'int': int, 'float': float, 'bool': bool,
        'range': range, 'enumerate': enumerate,
    },
    'datetime': datetime,           # Date/time operations
    'json': json,                   # JSON parsing
    'get_redis_client': get_redis_sync,  # Redis access
    'get_db': get_db,              # Database access
    'models': models,               # SQLAlchemy models
    'next': next,                   # Iterator function
}
```

### Error Handling

When a fetcher fails, it returns:
```python
{
    "failed_fetch": True,
    "error": "Description of what went wrong"
}
```

This prevents null values and allows templates to handle failures gracefully.

## Creating Data Fetchers

### Via Web Interface

1. Access the admin panel at `/html/admin.html`
2. Navigate to the "Data Fetchers" section
3. Click "Add New Fetcher"
4. Fill in the form:
   - **Fetcher Key**: Unique identifier (e.g., `current_weather`)
   - **Description**: What this fetcher does
   - **TTL Seconds**: How long to cache results
   - **Python Code**: The executable code block
   - **Active**: Enable/disable checkbox

### Via API

```bash
curl -X POST http://localhost:8000/api/data-fetchers \
  -H "Content-Type: application/json" \
  -d '{
    "fetcher_key": "system_status",
    "description": "System health and status information",
    "ttl_seconds": 60,
    "python_code": "import datetime\nresult = {\n    \"uptime\": \"24h 30m\",\n    \"timestamp\": datetime.datetime.now().isoformat()\n}",
    "is_active": true
  }'
```

### Code Structure

Your Python code must set a `result` variable:

```python
import datetime
import json

# Your data fetching logic here
data = {
    "timestamp": datetime.datetime.now().isoformat(),
    "status": "healthy"
}

# Set the result variable (required)
result = data
```

## Common Use Cases

### 1. Current Time and Date

```python
import datetime

result = {
    "current_time": datetime.datetime.now().isoformat(),
    "unix_timestamp": int(datetime.datetime.now().timestamp()),
    "readable_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
    "time": datetime.datetime.now().strftime("%H:%M:%S"),
    "day_of_week": datetime.datetime.now().strftime("%A"),
    "is_weekend": datetime.datetime.now().weekday() >= 5
}
```

**Usage in Template:**
```
Current time is {current_time[readable_time]}. Today is {current_time[day_of_week]}.
```

### 2. Home Assistant Device Status

```python
import json

r = get_redis_client()
try:
    cached_entities = r.get("ha:entities")
    if cached_entities:
        entities = json.loads(cached_entities)
        
        # Filter and organize data
        lights = [e for e in entities if e.get("entity_id", "").startswith("light.")]
        switches = [e for e in entities if e.get("entity_id", "").startswith("switch.")]
        
        result = {
            "total_devices": len(entities),
            "lights": {
                "count": len(lights),
                "on": len([l for l in lights if l.get("state") == "on"]),
                "off": len([l for l in lights if l.get("state") == "off"]),
                "entities": lights[:5]  # First 5 lights
            },
            "switches": {
                "count": len(switches),
                "on": len([s for s in switches if s.get("state") == "on"]),
                "entities": switches[:5]  # First 5 switches
            }
        }
    else:
        result = {"failed_fetch": True, "error": "No cached HA data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
```

**Usage in Template:**
```
There are {ha_device_status[lights][count]} lights, {ha_device_status[lights][on]} are currently on.
```

### 3. Active Rules from Database

```python
db = next(get_db())
try:
    rules = db.query(models.Rule).all()
    
    # Categorize rules
    guardrails = [r for r in rules if r.trigger_entity == "skippy"]
    automations = [r for r in rules if r.trigger_entity != "skippy"]
    
    result = {
        "total_rules": len(rules),
        "guardrails": {
            "count": len(guardrails),
            "rules": [
                {
                    "name": r.rule_name,
                    "target": r.target_entity,
                    "keywords": r.override_keywords
                } for r in guardrails
            ]
        },
        "automations": {
            "count": len(automations),
            "rules": [
                {
                    "name": r.rule_name,
                    "trigger": r.trigger_entity,
                    "target": r.target_entity
                } for r in automations
            ]
        }
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
finally:
    db.close()
```

### 4. Filtered Entity Lists

```python
import json

r = get_redis_client()
try:
    cached_entities = r.get("ha:entities")
    if cached_entities:
        all_entities = json.loads(cached_entities)
        
        # Filter specific entity types
        lights = [e for e in all_entities if e.get("entity_id", "").startswith("light.")]
        climate = [e for e in all_entities if e.get("entity_id", "").startswith("climate.")]
        sensors = [e for e in all_entities if e.get("entity_id", "").startswith("sensor.")]
        
        result = {
            "lights": lights,
            "climate": climate,
            "temperature_sensors": [
                s for s in sensors 
                if "temperature" in s.get("entity_id", "").lower()
            ],
            "motion_sensors": [
                s for s in sensors 
                if "motion" in s.get("entity_id", "").lower()
            ]
        }
    else:
        result = {"failed_fetch": True, "error": "No cached HA data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
```

### 5. Weather and Environmental Data

```python
import datetime
import json

# Get weather sensors from Home Assistant data
r = get_redis_client()
try:
    cached_entities = r.get("ha:entities")
    if cached_entities:
        entities = json.loads(cached_entities)
        
        # Find weather-related sensors
        weather_sensors = [
            e for e in entities 
            if any(keyword in e.get("entity_id", "").lower() 
                   for keyword in ["weather", "temperature", "humidity", "pressure"])
        ]
        
        # Extract current conditions
        current_temp = None
        current_humidity = None
        
        for sensor in weather_sensors:
            if "temperature" in sensor.get("entity_id", ""):
                current_temp = sensor.get("state")
            elif "humidity" in sensor.get("entity_id", ""):
                current_humidity = sensor.get("state")
        
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "temperature": current_temp,
            "humidity": current_humidity,
            "weather_sensors_count": len(weather_sensors),
            "conditions": {
                "comfortable_temp": 20 <= float(current_temp or 0) <= 25 if current_temp else False,
                "high_humidity": float(current_humidity or 0) > 70 if current_humidity else False
            }
        }
    else:
        result = {"failed_fetch": True, "error": "No weather data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
```

### 6. System Performance Metrics

```python
import datetime
import json

# Get system information from Redis or compute it
r = get_redis_client()

try:
    # Get cached entity count as a proxy for system activity
    cached_entities = r.get("ha:entities")
    entity_count = 0
    
    if cached_entities:
        entities = json.loads(cached_entities)
        entity_count = len(entities)
    
    # Get database connection info
    db = next(get_db())
    try:
        # Count total rules and templates
        rule_count = db.query(models.Rule).count()
        template_count = db.query(models.PromptTemplate).count()
        fetcher_count = db.query(models.DataFetcher).filter(models.DataFetcher.is_active == 1).count()
        
        result = {
            "timestamp": datetime.datetime.now().isoformat(),
            "system": {
                "ha_entities": entity_count,
                "total_rules": rule_count,
                "prompt_templates": template_count,
                "active_fetchers": fetcher_count,
                "uptime_estimate": "Available since last restart"
            },
            "health": {
                "database": "connected",
                "redis": "connected",
                "home_assistant": "connected" if entity_count > 0 else "no_data"
            }
        }
    finally:
        db.close()
        
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
```

## API Reference

### List All Data Fetchers
```http
GET /api/data-fetchers
```

### Create Data Fetcher
```http
POST /api/data-fetchers
Content-Type: application/json

{
  "fetcher_key": "string",
  "description": "string", 
  "ttl_seconds": 300,
  "python_code": "string",
  "is_active": true
}
```

### Get Specific Data Fetcher
```http
GET /api/data-fetchers/{fetcher_key}
```

### Update Data Fetcher
```http
PUT /api/data-fetchers/{fetcher_key}
Content-Type: application/json

{
  "description": "Updated description",
  "ttl_seconds": 600
}
```

### Delete Data Fetcher
```http
DELETE /api/data-fetchers/{fetcher_key}
```

### Test Data Fetcher (No Caching)
```http
GET /api/data-fetchers/{fetcher_key}/test
```

### Force Refresh Cache
```http
POST /api/data-fetchers/{fetcher_key}/refresh
```

## Best Practices

### 1. **Error Handling**
Always wrap your code in try/except blocks:

```python
try:
    # Your data fetching logic
    result = {"data": "success"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
```

### 2. **Resource Management**
Close database connections properly:

```python
db = next(get_db())
try:
    # Database operations
    result = {"data": "from_db"}
finally:
    db.close()
```

### 3. **Appropriate TTL Values**
- **Rapidly changing data** (current time, live sensors): 60-300 seconds
- **Moderately changing data** (device status, weather): 300-600 seconds  
- **Slowly changing data** (rules, configuration): 600-3600 seconds
- **Static reference data**: 3600+ seconds

### 4. **Data Size Optimization**
Keep returned data reasonably sized:

```python
# Good: Return summary data
result = {
    "light_count": len(lights),
    "lights_on": len([l for l in lights if l.get("state") == "on"]),
    "sample_lights": lights[:5]  # Just first 5
}

# Avoid: Returning massive datasets
# result = {"all_entities": huge_list_of_thousands}
```

### 5. **Descriptive Keys and Values**
Use clear, descriptive keys in your result data:

```python
result = {
    "current_temperature_celsius": 22.5,
    "humidity_percentage": 65,
    "is_heating_active": False,
    "comfort_level": "optimal"
}
```

## Troubleshooting

### Common Issues

#### 1. **Import Errors**
```
Error: __import__ not found
```
**Solution**: The execution environment includes common built-ins. For complex imports, ensure they're in the safe environment.

#### 2. **Redis Connection Issues**
```
Error: There is no current event loop in thread
```
**Solution**: Use `get_redis_client()` which provides a synchronous Redis client.

#### 3. **Database Connection Issues**
```
Error: Database connection failed
```
**Solution**: Always use the pattern:
```python
db = next(get_db())
try:
    # database operations
finally:
    db.close()
```

#### 4. **Caching Issues**
If data seems stale, check:
- TTL settings are appropriate
- Use `/refresh` endpoint to force cache update
- Check Redis connectivity

#### 5. **JSON Serialization Errors**
Ensure all data in `result` is JSON-serializable:
```python
# Good
result = {
    "timestamp": datetime.datetime.now().isoformat(),  # Convert to string
    "count": int(count),  # Ensure it's an int
    "active": bool(status)  # Ensure it's a boolean
}

# Bad - will cause serialization errors
# result = {
#     "timestamp": datetime.datetime.now(),  # datetime objects aren't JSON serializable
#     "count": numpy.int64(count)  # NumPy types aren't JSON serializable
# }
```

### Debugging Tips

1. **Use the Test Endpoint**: `/api/data-fetchers/{key}/test` bypasses caching and shows immediate results
2. **Check Logs**: The server logs all fetch operations and errors
3. **Start Simple**: Begin with basic code and add complexity gradually
4. **Validate Data**: Ensure your result data is properly structured

### Performance Monitoring

Monitor your data fetchers:
- Check execution time in server logs
- Monitor Redis memory usage for cached data
- Use appropriate TTL values to balance freshness vs. performance
- Consider the size of returned data

## Integration with Prompt Templates

Once you've created data fetchers, use them in prompt templates by adding their keys to the `pre_fetch_data` array:

```json
{
  "template_name": "Smart Home Control",
  "intent_keywords": "home,control,automate",
  "system_prompt": "You control a smart home system...",
  "user_template": "Current status: {ha_device_status} at {current_time}. Rules: {rules_list}",
  "pre_fetch_data": ["ha_device_status", "current_time", "rules_list"]
}
```

The fetched data will be available as template variables using the fetcher key names.