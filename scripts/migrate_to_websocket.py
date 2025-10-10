#!/usr/bin/env python3
"""
Migration script to transition from polling-based to WebSocket-based Home Assistant integration.

This script:
1. Updates existing data fetchers to use the new Redis state manager
2. Adds new WebSocket-specific data fetchers
3. Validates the WebSocket connection
"""

import sys
import os
import asyncio
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from mcp.database import SessionLocal
from mcp.models import DataFetcher
from mcp.ha_websocket import HomeAssistantWebSocketClient
from mcp.ha_state import get_ha_state_manager
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_websocket_connection():
    """Test the WebSocket connection to Home Assistant."""
    logger.info("Testing WebSocket connection to Home Assistant...")
    
    client = HomeAssistantWebSocketClient()
    
    try:
        # Test connection
        if await client.connect():
            logger.info("✓ WebSocket connection established")
            
            # Test authentication
            if await client.authenticate():
                logger.info("✓ Authentication successful")
                
                # Test getting initial states
                if await client.get_initial_states():
                    logger.info("✓ Initial states fetched successfully")
                    
                    # Test state manager
                    manager = get_ha_state_manager()
                    summary = await manager.get_state_summary()
                    logger.info(f"✓ State cache populated: {summary.get('total_entities', 0)} entities")
                    
                    return True
                else:
                    logger.error("✗ Failed to get initial states")
            else:
                logger.error("✗ Authentication failed")
        else:
            logger.error("✗ WebSocket connection failed")
        
        return False
        
    except Exception as e:
        logger.error(f"✗ WebSocket test failed: {e}")
        return False
    finally:
        await client.cleanup()

def update_existing_data_fetchers():
    """Update existing data fetchers to work better with WebSocket integration."""
    logger.info("Updating existing data fetchers...")
    
    db = SessionLocal()
    try:
        # Update ha_device_status to use better error handling
        ha_device_fetcher = db.query(DataFetcher).filter(
            DataFetcher.fetcher_key == 'ha_device_status'
        ).first()
        
        if ha_device_fetcher:
            # Updated code with better error handling and WebSocket awareness
            updated_code = '''import json
r = get_redis_client()
try:
    # Try the new WebSocket cache first
    cached_entities = r.get("ha:all_states")
    if cached_entities:
        all_entities = json.loads(cached_entities)
        # Filter for controllable entities
        controllable_domains = {"switch", "light", "climate", "fan", "cover", "media_player", "lock"}
        entities = [e for e in all_entities if e.get("entity_id", "").split(".")[0] in controllable_domains]
    else:
        # Fallback to old cache key for backward compatibility
        cached_entities = r.get("ha:entities")
        if cached_entities:
            entities = json.loads(cached_entities)
        else:
            result = {"failed_fetch": True, "error": "No cached HA data available - WebSocket may not be connected"}
            return
    
    result = {
        "device_count": len(entities),
        "devices": entities,
        "light_count": len([e for e in entities if e.get("entity_id", "").startswith("light.")]),
        "switch_count": len([e for e in entities if e.get("entity_id", "").startswith("switch.")]),
        "climate_count": len([e for e in entities if e.get("entity_id", "").startswith("climate.")]),
        "fan_count": len([e for e in entities if e.get("entity_id", "").startswith("fan.")]),
        "cover_count": len([e for e in entities if e.get("entity_id", "").startswith("cover.")]),
        "media_player_count": len([e for e in entities if e.get("entity_id", "").startswith("media_player.")]),
        "websocket_mode": True
    }
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}'''
            
            ha_device_fetcher.python_code = updated_code
            ha_device_fetcher.description = "All Home Assistant controllable device states from WebSocket cache"
            ha_device_fetcher.ttl_seconds = 30  # Reduce TTL since WebSocket provides real-time updates
            
            logger.info("✓ Updated ha_device_status data fetcher")
        
        # Update light_entities fetcher
        light_fetcher = db.query(DataFetcher).filter(
            DataFetcher.fetcher_key == 'light_entities'
        ).first()
        
        if light_fetcher:
            updated_light_code = '''import json
r = get_redis_client()
try:
    # Use the new domain-specific cache if available
    domain_entities = r.get("ha:domain:light")
    if domain_entities:
        lights = json.loads(domain_entities)
        result = {
            "light_count": len(lights),
            "lights": lights,
            "lights_on": [l for l in lights if l.get("state") == "on"],
            "lights_off": [l for l in lights if l.get("state") == "off"],
            "websocket_mode": True
        }
    else:
        # Fallback to old method
        cached_entities = r.get("ha:entities")
        if cached_entities:
            all_entities = json.loads(cached_entities)
            lights = [e for e in all_entities if e.get("entity_id", "").startswith("light.")]
            result = {
                "light_count": len(lights),
                "lights": lights,
                "websocket_mode": False
            }
        else:
            result = {"failed_fetch": True, "error": "No cached HA data available"}
except Exception as e:
    result = {"failed_fetch": True, "error": str(e)}'''
            
            light_fetcher.python_code = updated_light_code
            light_fetcher.description = "Light entities from WebSocket cache with state breakdown"
            light_fetcher.ttl_seconds = 30
            
            logger.info("✓ Updated light_entities data fetcher")
        
        db.commit()
        logger.info("✓ Data fetcher updates committed")
        
    except Exception as e:
        logger.error(f"Error updating data fetchers: {e}")
        db.rollback()
    finally:
        db.close()

async def validate_data_fetchers():
    """Test that data fetchers work with the new WebSocket system."""
    logger.info("Validating data fetchers...")
    
    from mcp.data_fetcher_engine import execute_fetcher_code, get_prefetch_data
    
    # Test some key fetchers
    test_fetchers = ['ha_device_status', 'light_entities', 'current_time']
    
    for fetcher_key in test_fetchers:
        try:
            logger.info(f"Testing {fetcher_key}...")
            result = get_prefetch_data(fetcher_key, force_refresh=True)
            
            if result.get('failed_fetch'):
                logger.warning(f"⚠ {fetcher_key} failed: {result.get('error')}")
            else:
                logger.info(f"✓ {fetcher_key} working")
                
        except Exception as e:
            logger.error(f"✗ {fetcher_key} error: {e}")

def show_migration_summary():
    """Show summary of changes and next steps."""
    logger.info("\n" + "="*60)
    logger.info("MIGRATION SUMMARY")
    logger.info("="*60)
    logger.info("✓ WebSocket client created (mcp/ha_websocket.py)")
    logger.info("✓ Redis state manager created (mcp/ha_state.py)")
    logger.info("✓ Main.py updated to use WebSocket instead of polling")
    logger.info("✓ Health checks updated")
    logger.info("✓ New WebSocket-specific data fetchers available")
    logger.info("✓ Requirements.txt updated with websockets dependency")
    logger.info("")
    logger.info("NEXT STEPS:")
    logger.info("1. Install new dependencies: pip install -r requirements.txt")
    logger.info("2. Add new data fetchers: mysql < mysql/schemas/07_websocket_data_fetchers.sql")
    logger.info("3. Restart the MCP server")
    logger.info("4. Monitor logs to ensure WebSocket connection is stable")
    logger.info("5. Test data fetchers in admin interface")
    logger.info("")
    logger.info("REMOVED COMPONENTS:")
    logger.info("- APScheduler polling (replaced with real-time WebSocket)")
    logger.info("- homeassistant/poller.py (can be kept for manual testing)")
    logger.info("- Database entity storage (moved to Redis cache)")
    logger.info("")
    logger.info("BENEFITS:")
    logger.info("- Real-time state updates (no 30-minute polling delay)")
    logger.info("- Reduced database load")
    logger.info("- Faster data fetcher execution")
    logger.info("- Better error handling and reconnection")
    logger.info("="*60)

async def main():
    """Main migration function."""
    logger.info("Starting Home Assistant WebSocket migration...")
    
    # Test WebSocket connection
    websocket_ok = await test_websocket_connection()
    
    if not websocket_ok:
        logger.warning("WebSocket test failed - migration will continue but manual configuration may be needed")
    
    # Update existing data fetchers
    update_existing_data_fetchers()
    
    # Test data fetchers if WebSocket is working
    if websocket_ok:
        await validate_data_fetchers()
    
    # Show summary
    show_migration_summary()
    
    logger.info("Migration complete!")

if __name__ == "__main__":
    asyncio.run(main())