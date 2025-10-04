-- Sample data fetchers for common use cases
INSERT INTO data_fetchers (fetcher_key, description, ttl_seconds, python_code, is_active) VALUES 
('current_time', 'Current timestamp and date information', 300, 
'import datetime
result = {
    "current_time": datetime.datetime.now().isoformat(),
    "unix_timestamp": int(datetime.datetime.now().timestamp()),
    "readable_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "date": datetime.datetime.now().strftime("%Y-%m-%d"),
    "time": datetime.datetime.now().strftime("%H:%M:%S")
}', 1),

('ha_device_status', 'All Home Assistant device states from Redis cache', 60,
'import json
r = get_redis_client()
try:
    cached_entities = r.get("ha:entities")
    if cached_entities:
        entities = json.loads(cached_entities)
        result = {
            "device_count": len(entities),
            "devices": entities,
            "light_count": len([e for e in entities if e.get("entity_id", "").startswith("light.")]),
            "switch_count": len([e for e in entities if e.get("entity_id", "").startswith("switch.")]),
            "sensor_count": len([e for e in entities if e.get("entity_id", "").startswith("sensor.")])
        }
    else:
        result = {"failed_fetch": True, "error": "No cached HA data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('rules_list', 'Active rules from the database', 120,
'db = next(get_db())
try:
    rules = db.query(models.Rule).all()
    result = {
        "rule_count": len(rules),
        "rules": [
            {
                "id": rule.id,
                "name": rule.rule_name,
                "type": rule.rule_type,
                "description": rule.description,
                "active": bool(rule.is_active),
                "priority": rule.priority
            } for rule in rules
        ]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}
finally:
    db.close()', 1),

('light_entities', 'Only light/lamp entities from Home Assistant', 60,
'import json
r = get_redis_client()
try:
    cached_entities = r.get("ha:entities")
    if cached_entities:
        all_entities = json.loads(cached_entities)
        lights = [e for e in all_entities if e.get("entity_id", "").startswith("light.")]
        result = {
            "light_count": len(lights),
            "lights": lights
        }
    else:
        result = {"failed_fetch": True, "error": "No cached HA data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1);