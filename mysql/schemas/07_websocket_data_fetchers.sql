-- Enhanced data fetchers for WebSocket-based Home Assistant integration
-- Run these after the WebSocket client is implemented

INSERT INTO data_fetchers (fetcher_key, description, ttl_seconds, python_code, is_active) VALUES 

('ha_lights_on', 'All lights that are currently on', 30,
'from mcp.ha_state import get_ha_lights_on
import asyncio

try:
    lights_on = asyncio.run(get_ha_lights_on())
    result = {
        "lights_on_count": len(lights_on),
        "lights_on": lights_on,
        "entity_ids": [light.get("entity_id") for light in lights_on],
        "friendly_names": [light.get("attributes", {}).get("friendly_name", light.get("entity_id")) for light in lights_on]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_switches_on', 'All switches that are currently on', 30,
'from mcp.ha_state import get_ha_switches_on
import asyncio

try:
    switches_on = asyncio.run(get_ha_switches_on())
    result = {
        "switches_on_count": len(switches_on),
        "switches_on": switches_on,
        "entity_ids": [switch.get("entity_id") for switch in switches_on],
        "friendly_names": [switch.get("attributes", {}).get("friendly_name", switch.get("entity_id")) for switch in switches_on]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_domain_lights', 'All light entities with current states', 60,
'from mcp.ha_state import get_ha_domain_entities
import asyncio

try:
    lights = asyncio.run(get_ha_domain_entities("light"))
    on_lights = [l for l in lights if l.get("state") == "on"]
    off_lights = [l for l in lights if l.get("state") == "off"]
    
    result = {
        "total_lights": len(lights),
        "lights_on": len(on_lights),
        "lights_off": len(off_lights),
        "all_lights": lights,
        "on_light_names": [l.get("attributes", {}).get("friendly_name", l.get("entity_id")) for l in on_lights],
        "off_light_names": [l.get("attributes", {}).get("friendly_name", l.get("entity_id")) for l in off_lights]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_domain_switches', 'All switch entities with current states', 60,
'from mcp.ha_state import get_ha_domain_entities
import asyncio

try:
    switches = asyncio.run(get_ha_domain_entities("switch"))
    on_switches = [s for s in switches if s.get("state") == "on"]
    off_switches = [s for s in switches if s.get("state") == "off"]
    
    result = {
        "total_switches": len(switches),
        "switches_on": len(on_switches),
        "switches_off": len(off_switches),
        "all_switches": switches,
        "on_switch_names": [s.get("attributes", {}).get("friendly_name", s.get("entity_id")) for s in on_switches],
        "off_switch_names": [s.get("attributes", {}).get("friendly_name", s.get("entity_id")) for s in off_switches]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_state_summary', 'Summary of Home Assistant state cache', 120,
'from mcp.ha_state import get_ha_state_manager
import asyncio

try:
    manager = get_ha_state_manager()
    summary = asyncio.run(manager.get_state_summary())
    is_healthy = asyncio.run(manager.is_cache_healthy())
    
    result = {
        "cache_healthy": is_healthy,
        "last_update": summary.get("last_update"),
        "total_entities": summary.get("total_entities", 0),
        "controllable_entities": summary.get("controllable_entities", 0),
        "available_domains": summary.get("available_domains", []),
        "domain_count": summary.get("domain_count", 0)
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_specific_entity', 'Get a specific entity by ID (requires entity_id parameter)', 30,
'from mcp.ha_state import get_ha_entity
import asyncio

# This fetcher expects an entity_id to be set in context
# For now, we''ll use a default or show example usage
entity_id = "light.living_room"  # Default example

try:
    entity = asyncio.run(get_ha_entity(entity_id))
    if entity:
        result = {
            "entity_found": True,
            "entity_id": entity.get("entity_id"),
            "state": entity.get("state"),
            "friendly_name": entity.get("attributes", {}).get("friendly_name"),
            "domain": entity.get("entity_id", "").split(".")[0],
            "attributes": entity.get("attributes", {}),
            "last_changed": entity.get("last_changed"),
            "last_updated": entity.get("last_updated")
        }
    else:
        result = {"entity_found": False, "entity_id": entity_id, "error": "Entity not found"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1),

('ha_search_pattern', 'Search entities by name pattern (requires pattern parameter)', 30,
'from mcp.ha_state import search_ha_entities
import asyncio

# This fetcher expects a pattern to be set in context
# For now, we''ll use a default or show example usage
pattern = "living"  # Default example - searches for entities with "living" in the name

try:
    entities = asyncio.run(search_ha_entities(pattern))
    result = {
        "pattern_searched": pattern,
        "entities_found": len(entities),
        "entities": entities,
        "entity_ids": [e.get("entity_id") for e in entities],
        "friendly_names": [e.get("attributes", {}).get("friendly_name", e.get("entity_id")) for e in entities]
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}', 1);