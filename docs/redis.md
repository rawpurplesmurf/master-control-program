# Redis Data Storage and Cache Management

MCP (Master Control Program) uses Redis extensively for caching Home Assistant entity states, logging state changes, storing WebSocket messages, and maintaining various system data. This document provides a comprehensive overview of all Redis keys and patterns used throughout the system.

## Overview

Redis serves as the primary cache and logging backend for MCP, providing:
- **Real-time entity state caching** from Home Assistant WebSocket
- **State change logging** with 7-day retention
- **Data fetcher result caching** with configurable TTL
- **WebSocket message debugging** and troubleshooting
- **System health monitoring** and diagnostics

## Redis Key Patterns

### 1. Home Assistant Entity State Cache

#### Individual Entity Cache
```
Key Pattern: ha:entity:{entity_id}
Type: String (JSON)
TTL: 1 hour (3600 seconds)
Example: ha:entity:light.living_room
```

**Purpose**: Stores the complete state object for individual Home Assistant entities.

**Sample Commands**:
```bash
# Get entity state
redis-cli get "ha:entity:light.living_room"

# List all cached entities
redis-cli keys "ha:entity:*"

# Check TTL for entity
redis-cli ttl "ha:entity:light.living_room"

# Get entity count
redis-cli eval "return #redis.call('keys', 'ha:entity:*')" 0
```

**Sample Data**:
```json
{
  "entity_id": "light.living_room",
  "state": "on",
  "attributes": {
    "brightness": 255,
    "color_mode": "brightness",
    "friendly_name": "Living Room Light",
    "supported_features": 40
  },
  "last_changed": "2025-10-04T06:30:15.123456+00:00",
  "last_reported": "2025-10-04T06:30:15.123456+00:00",
  "last_updated": "2025-10-04T06:30:15.123456+00:00"
}
```

#### All States Cache
```
Key Pattern: ha:all_states
Type: String (JSON Array)
TTL: 1 hour (3600 seconds)
```

**Purpose**: Stores complete array of all Home Assistant entity states for bulk operations.

**Sample Commands**:
```bash
# Get all entity states
redis-cli get "ha:all_states"

# Check size of all states data
redis-cli strlen "ha:all_states"

# Get TTL
redis-cli ttl "ha:all_states"
```

#### Domain-Grouped Cache
```
Key Pattern: ha:domain:{domain}
Type: String (JSON Array)
TTL: 1 hour (3600 seconds)
Examples: ha:domain:light, ha:domain:switch, ha:domain:climate
```

**Purpose**: Groups entities by domain (light, switch, etc.) for efficient domain-specific queries.

**Sample Commands**:
```bash
# Get all lights
redis-cli get "ha:domain:light"

# Get all switches
redis-cli get "ha:domain:switch"

# List all domain caches
redis-cli keys "ha:domain:*"

# Count entities by domain
redis-cli eval "local keys = redis.call('keys', 'ha:domain:*'); local result = {}; for i=1,#keys do local data = redis.call('get', keys[i]); if data then local json = cjson.decode(data); table.insert(result, keys[i] .. ':' .. #json); end; end; return result" 0
```

#### Controllable Entities Cache
```
Key Pattern: ha:controllable
Type: String (JSON Array)
TTL: 1 hour (3600 seconds)
```

**Purpose**: Cached list of entities that can be controlled (lights, switches, climate, fans, etc.).

**Sample Commands**:
```bash
# Get controllable entities
redis-cli get "ha:controllable"

# Count controllable entities
redis-cli eval "local data = redis.call('get', 'ha:controllable'); if data then return #cjson.decode(data); else return 0; end" 0
```

#### Cache Metadata
```
Key Pattern: ha:cache_metadata
Type: String (JSON)
TTL: 1 hour (3600 seconds)
```

**Purpose**: Stores metadata about the cache including last update time and entity counts.

**Sample Commands**:
```bash
# Get cache metadata
redis-cli get "ha:cache_metadata"

# Check cache health (last update time)
redis-cli eval "local meta = redis.call('get', 'ha:cache_metadata'); if meta then local data = cjson.decode(meta); return data.last_update; else return 'no_data'; end" 0
```

### 2. Entity State Change Logging

#### Individual Entity Logs
```
Key Pattern: ha:log:{entity_id}
Type: Sorted Set (ZSET)
TTL: 7 days (604800 seconds)
Score: Unix timestamp
Example: ha:log:light.living_room
```

**Purpose**: Logs all state changes for individual entities with chronological ordering.

**Sample Commands**:
```bash
# Get recent log entries for entity (newest first)
redis-cli zrevrange "ha:log:light.living_room" 0 9 withscores

# Get logs within time range
redis-cli zrangebyscore "ha:log:light.living_room" 1696377600 1696464000 withscores

# Count log entries for entity
redis-cli zcard "ha:log:light.living_room"

# Get oldest log entry
redis-cli zrange "ha:log:light.living_room" 0 0 withscores

# Get newest log entry
redis-cli zrevrange "ha:log:light.living_room" 0 0 withscores

# Remove old entries (older than 7 days)
redis-cli eval "local cutoff = ARGV[1]; return redis.call('zremrangebyscore', KEYS[1], 0, cutoff)" 1 "ha:log:light.living_room" "$(date -d '7 days ago' +%s)"
```

**Sample Data**:
```json
{
  "timestamp": "2025-10-04T06:30:15.123456Z",
  "entity_id": "light.living_room",
  "old_state": {
    "state": "off",
    "attributes": {"brightness": 0, "friendly_name": "Living Room Light"}
  },
  "new_state": {
    "state": "on", 
    "attributes": {"brightness": 255, "friendly_name": "Living Room Light"}
  },
  "state_changed": true,
  "attributes_changed": true
}
```

#### Global Entity Logs
```
Key Pattern: ha:log:all
Type: Sorted Set (ZSET)
TTL: 7 days (604800 seconds)
Score: Unix timestamp
```

**Purpose**: Master log containing all entity state changes across the system.

**Sample Commands**:
```bash
# Get recent global logs (all entities)
redis-cli zrevrange "ha:log:all" 0 19 withscores

# Count total log entries
redis-cli zcard "ha:log:all"

# Get logs from last hour
redis-cli zrangebyscore "ha:log:all" "$(date -d '1 hour ago' +%s)" "$(date +%s)" withscores

# Get entities with logs
redis-cli eval "local logs = redis.call('zrange', 'ha:log:all', 0, -1); local entities = {}; for i=1,#logs do local data = cjson.decode(logs[i]); entities[data.entity_id] = true; end; local result = {}; for k,v in pairs(entities) do table.insert(result, k); end; return result" 0
```

### 3. Data Fetcher Cache

#### Individual Fetcher Results
```
Key Pattern: data_fetcher:{fetcher_key}
Type: String (JSON)
TTL: Configurable per fetcher (default 300 seconds)
Examples: data_fetcher:current_time, data_fetcher:ha_device_status
```

**Purpose**: Caches results from data fetcher executions to avoid repeated computations.

**Sample Commands**:
```bash
# Get cached result for fetcher
redis-cli get "data_fetcher:current_time"

# List all cached fetchers
redis-cli keys "data_fetcher:*"

# Check TTL for fetcher cache
redis-cli ttl "data_fetcher:ha_device_status"

# Clear specific fetcher cache
redis-cli del "data_fetcher:current_time"

# Clear all fetcher caches
redis-cli eval "local keys = redis.call('keys', 'data_fetcher:*'); for i=1,#keys do redis.call('del', keys[i]); end; return #keys" 0
```

**Sample Data**:
```json
{
  "result": {
    "timestamp": "2025-10-04T06:30:15.123456Z",
    "formatted_time": "October 4, 2025 at 6:30 AM"
  },
  "execution_time": 0.001234,
  "cached_at": "2025-10-04T06:30:15.123456Z"
}
```

### 4. WebSocket Message Debugging

#### Recent WebSocket Messages
```
Key Pattern: ha:websocket:messages
Type: List
TTL: 1 hour (3600 seconds)
```

**Purpose**: Stores recent WebSocket messages for debugging and troubleshooting.

**Sample Commands**:
```bash
# Get recent WebSocket messages
redis-cli lrange "ha:websocket:messages" 0 9

# Count stored messages
redis-cli llen "ha:websocket:messages"

# Get oldest message
redis-cli lindex "ha:websocket:messages" -1

# Get newest message  
redis-cli lindex "ha:websocket:messages" 0

# Clear message history
redis-cli del "ha:websocket:messages"
```

### 5. Prompt History and LLM Interactions

#### Command Processing History
```
Key Pattern: prompt_history:{interaction_id}
Type: String (JSON)
TTL: 24 hours (86400 seconds)
```

**Purpose**: Stores complete command processing pipeline results for audit and debugging.

**Sample Commands**:
```bash
# Get specific interaction
redis-cli get "prompt_history:1234567890"

# List all prompt history keys
redis-cli keys "prompt_history:*"

# Count interactions
redis-cli eval "return #redis.call('keys', 'prompt_history:*')" 0

# Get recent interactions (by key pattern)
redis-cli eval "local keys = redis.call('keys', 'prompt_history:*'); table.sort(keys); return {unpack(keys, math.max(1, #keys-9), #keys)}" 0
```

## Redis Health Monitoring

### System Health Commands

```bash
# Check Redis connectivity
redis-cli ping

# Get Redis info
redis-cli info

# Check memory usage
redis-cli info memory

# Get database size
redis-cli dbsize

# Check connected clients
redis-cli info clients

# Monitor Redis commands in real-time
redis-cli monitor

# Get slow queries
redis-cli slowlog get 10
```

### MCP-Specific Health Checks

```bash
# Check if WebSocket is populating data
redis-cli exists "ha:all_states"

# Verify entity logging is working
redis-cli zcard "ha:log:all"

# Check cache freshness
redis-cli eval "local meta = redis.call('get', 'ha:cache_metadata'); if meta then local data = cjson.decode(meta); local age = tonumber(ARGV[1]) - tonumber(data.last_update or 0); return age < 3600 and 'fresh' or 'stale'; else return 'missing'; end" 0 "$(date +%s)"

# Count entities by domain
redis-cli eval "local domains = {'light', 'switch', 'climate', 'sensor', 'binary_sensor'}; local result = {}; for i=1,#domains do local key = 'ha:domain:' .. domains[i]; local data = redis.call('get', key); if data then local entities = cjson.decode(data); table.insert(result, domains[i] .. ':' .. #entities); else table.insert(result, domains[i] .. ':0'); end; end; return result" 0
```

### Performance Monitoring

```bash
# Check key expiration times
redis-cli eval "local keys = redis.call('keys', 'ha:*'); local result = {}; for i=1,#keys do local ttl = redis.call('ttl', keys[i]); table.insert(result, keys[i] .. ':' .. ttl); end; return result" 0

# Memory usage by key pattern
redis-cli eval "local keys = redis.call('keys', ARGV[1]); local total = 0; for i=1,#keys do local mem = redis.call('memory', 'usage', keys[i]); total = total + (mem or 0); end; return total" 0 "ha:*"

# Check for keys without TTL (potential memory leaks)
redis-cli eval "local keys = redis.call('keys', '*'); local no_ttl = {}; for i=1,#keys do local ttl = redis.call('ttl', keys[i]); if ttl == -1 then table.insert(no_ttl, keys[i]); end; end; return no_ttl" 0
```

## Maintenance and Cleanup

### Regular Maintenance Commands

```bash
# Clean up expired entity logs (older than 7 days)
redis-cli eval "local keys = redis.call('keys', 'ha:log:*'); local cutoff = ARGV[1]; local cleaned = 0; for i=1,#keys do local removed = redis.call('zremrangebyscore', keys[i], 0, cutoff); cleaned = cleaned + removed; end; return cleaned" 0 "$(date -d '7 days ago' +%s)"

# Remove empty log keys
redis-cli eval "local keys = redis.call('keys', 'ha:log:*'); local removed = {}; for i=1,#keys do local count = redis.call('zcard', keys[i]); if count == 0 then redis.call('del', keys[i]); table.insert(removed, keys[i]); end; end; return removed" 0

# Refresh all TTLs for entity cache
redis-cli eval "local keys = redis.call('keys', 'ha:entity:*'); for i=1,#keys do redis.call('expire', keys[i], 3600); end; return #keys" 0

# Clear all data fetcher caches
redis-cli eval "local keys = redis.call('keys', 'data_fetcher:*'); for i=1,#keys do redis.call('del', keys[i]); end; return #keys" 0
```

### Emergency Procedures

```bash
# Clear all Home Assistant cache (force refresh)
redis-cli eval "local keys = redis.call('keys', 'ha:*'); for i=1,#keys do if not string.match(keys[i], 'ha:log:') then redis.call('del', keys[i]); end; end; return 'cache_cleared'" 0

# Emergency: Clear all MCP data (nuclear option)
redis-cli flushdb

# Backup specific key patterns
redis-cli --rdb /backup/mcp_backup.rdb
```

## Configuration and Best Practices

### Redis Configuration Recommendations

```ini
# redis.conf recommendations for MCP
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

### Monitoring Alerts

Set up monitoring for:
- Redis memory usage > 80%
- Keys without TTL (memory leaks)
- Cache age > 1 hour (stale data)
- Log retention > 7 days (cleanup needed)
- Entity log count growth rate (anomaly detection)

### Performance Optimization

1. **Use pipelining** for bulk operations
2. **Set appropriate TTLs** to prevent memory bloat
3. **Monitor slow queries** and optimize Lua scripts
4. **Use sorted sets efficiently** for time-based queries
5. **Implement proper error handling** for Redis failures

This Redis setup provides comprehensive caching, logging, and debugging capabilities for the MCP system while maintaining performance and data integrity.