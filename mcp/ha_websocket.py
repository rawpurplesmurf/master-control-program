"""
Home Assistant WebSocket client for real-time state updates.
Maintains live entity state in Redis cache.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Set
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode
import aiohttp

from mcp.config import settings
from mcp.cache import get_redis_client

logger = logging.getLogger(__name__)
websocket_logger = logging.getLogger('mcp.websocket')

class HomeAssistantWebSocketClient:
    """WebSocket client for Home Assistant that maintains Redis state cache."""
    
    def __init__(self):
        self.ha_url = settings.HA_URL
        self.websocket = None
        self.redis_client = None
        self.message_id = 1
        self.is_authenticated = False
        self.is_running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 60
        self.controllable_domains = {"switch", "light", "climate", "fan", "cover", "media_player", "lock", "scene"}
        self.recent_messages = []  # Store last 10 messages for debugging
        
    async def connect(self):
        """Connect to Home Assistant WebSocket API."""
        try:
            # Initialize Redis client
            self.redis_client = get_redis_client()
            if not self.redis_client:
                logger.error("Failed to get Redis client")
                return False
            websocket_logger.info("✅ REDIS CLIENT INITIALIZED")
            logger.info("Redis client initialized")
            
            websocket_url = f"ws://{self.ha_url.replace('http://', '').replace('https://', '')}/api/websocket"
            websocket_logger.info(f"🔌 CONNECTING TO: {websocket_url}")
            logger.info(f"Connecting to Home Assistant WebSocket: {websocket_url}")
            
            # Use asyncio.wait_for for timeout handling
            self.websocket = await asyncio.wait_for(
                websockets.connect(websocket_url),
                timeout=30
            )
            
            websocket_logger.info("✅ WEBSOCKET CONNECTION ESTABLISHED")
            logger.info("WebSocket connection established")
            return True
            
        except Exception as e:
            websocket_logger.error(f"❌ CONNECTION FAILED: {e}")
            logger.error(f"Failed to connect to WebSocket: {e}")
            return False
    
    async def authenticate(self):
        """Authenticate with Home Assistant using access token."""
        if not self.websocket:
            return False
            
        try:
            # Wait for auth_required message
            websocket_logger.info("🔑 WAITING FOR AUTH_REQUIRED MESSAGE...")
            auth_msg = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            auth_data = json.loads(auth_msg)
            
            websocket_logger.info(f"🔑 AUTH MESSAGE RECEIVED: {json.dumps(auth_data, indent=2)}")
            
            if auth_data.get("type") != "auth_required":
                websocket_logger.error(f"❌ EXPECTED auth_required, GOT: {auth_data}")
                logger.error(f"Unexpected initial message: {auth_data}")
                return False
            
            # Send authentication
            auth_response = {
                "type": "auth",
                "access_token": settings.HA_TOKEN
            }
            websocket_logger.info("🔑 SENDING AUTH RESPONSE...")
            await self.websocket.send(json.dumps(auth_response))
            
            # Wait for auth result
            websocket_logger.info("🔑 WAITING FOR AUTH RESULT...")
            result_msg = await asyncio.wait_for(self.websocket.recv(), timeout=10)
            result_data = json.loads(result_msg)
            
            websocket_logger.info(f"🔑 AUTH RESULT: {json.dumps(result_data, indent=2)}")
            
            if result_data.get("type") == "auth_ok":
                websocket_logger.info("✅ AUTHENTICATION SUCCESSFUL")
                logger.info("Successfully authenticated with Home Assistant")
                self.is_authenticated = True
                return True
            else:
                websocket_logger.error(f"❌ AUTHENTICATION FAILED: {result_data}")
                logger.error(f"Authentication failed: {result_data}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Authentication timed out")
            return False
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def subscribe_to_events(self):
        """Subscribe to state_changed events."""
        if not self.is_authenticated:
            return False
            
        subscribe_msg = {
            "id": self._next_message_id(),
            "type": "subscribe_events",
            "event_type": "state_changed"
        }
        
        try:
            websocket_logger.info(f"🔔 SENDING SUBSCRIPTION REQUEST: {json.dumps(subscribe_msg, indent=2)}")
            await self.websocket.send(json.dumps(subscribe_msg))
            logger.info(f"🔔 Sent subscription request: {json.dumps(subscribe_msg)}")
            
            websocket_logger.info("🔔 SUBSCRIPTION REQUEST SENT - CONFIRMATION WILL COME IN MESSAGE LOOP")
            
            # Don't wait for response here - it will be handled in the message loop
            # The subscription confirmation will come as a "result" message
            return True
            
        except Exception as e:
            websocket_logger.error(f"❌ SUBSCRIPTION FAILED: {e}")
            logger.error(f"Failed to subscribe to events: {e}")
            return False
    
    async def get_initial_states(self):
        """Fetch all current states and populate Redis cache."""
        if not self.is_authenticated:
            return False
            
        get_states_msg = {
            "id": self._next_message_id(),
            "type": "get_states"
        }
        
        try:
            await self.websocket.send(json.dumps(get_states_msg))
            
            # Wait for response
            response_msg = await asyncio.wait_for(self.websocket.recv(), timeout=30)
            response_data = json.loads(response_msg)
            
            if response_data.get("success"):
                states = response_data.get("result", [])
                await self._cache_states(states)
                logger.info(f"Cached {len(states)} initial entity states to Redis")
                return True
            else:
                logger.error(f"Failed to get initial states: {response_data}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for initial states")
            return False
        except Exception as e:
            logger.error(f"Error getting initial states: {e}")
            return False
    
    async def _cache_states(self, states):
        """Cache entity states to Redis."""
        if not self.redis_client:
            return
            
        try:
            # Cache all states
            all_states_key = "ha:all_states"
            await self.redis_client.setex(
                all_states_key, 
                3600,  # 1 hour expiry
                json.dumps(states)
            )
            
            # Cache individual entity states with domain grouping
            domain_groups = {}
            controllable_entities = []
            
            for state in states:
                entity_id = state.get("entity_id")
                if not entity_id:
                    continue
                    
                domain = entity_id.split(".")[0]
                
                # Cache individual entity
                entity_key = f"ha:entity:{entity_id}"
                await self.redis_client.setex(entity_key, 3600, json.dumps(state))
                
                # Group by domain
                if domain not in domain_groups:
                    domain_groups[domain] = []
                domain_groups[domain].append(state)
                
                # Track controllable entities
                if domain in self.controllable_domains:
                    controllable_entities.append(state)
            
            # Cache domain groups
            for domain, entities in domain_groups.items():
                domain_key = f"ha:domain:{domain}"
                await self.redis_client.setex(domain_key, 3600, json.dumps(entities))
            
            # Cache controllable entities (for backward compatibility)
            controllable_key = "ha:entities"
            await self.redis_client.setex(
                controllable_key, 
                3600, 
                json.dumps(controllable_entities)
            )
            
            # Update metadata
            metadata = {
                "last_update": datetime.utcnow().isoformat(),
                "total_entities": len(states),
                "controllable_entities": len(controllable_entities),
                "domains": list(domain_groups.keys())
            }
            await self.redis_client.setex("ha:metadata", 3600, json.dumps(metadata))
            
        except Exception as e:
            logger.error(f"Error caching states to Redis: {e}")
    
    async def _handle_state_change(self, event_data):
        """Handle a single state change event."""
        try:
            # Parse the nested event structure correctly
            event = event_data.get("event", {})
            data = event.get("data", {})
            entity_id = data.get("entity_id")
            new_state = data.get("new_state")
            old_state = data.get("old_state")
            
            # Add debugging
            old_state_str = old_state.get('state') if old_state else 'None'
            new_state_str = new_state.get('state') if new_state else 'None'
            logger.debug(f"🔄 State change received: {entity_id} | {old_state_str} → {new_state_str}")
            
            if not entity_id:
                logger.warning(f"Missing entity_id in state change data")
                return
            
            # Handle entity removal (when new_state is None)
            if new_state is None:
                logger.info(f"🗑️ Entity removed from Home Assistant: {entity_id}")
                await self._handle_entity_removal(entity_id, old_state)
                return
                
            # Update individual entity cache for existing entities
            entity_key = f"ha:entity:{entity_id}"
            await self.redis_client.setex(entity_key, 3600, json.dumps(new_state))
            
            # Log the state change with 7-day TTL
            logger.debug(f"🔄 About to log state change for {entity_id}")
            await self._log_state_change(entity_id, old_state, new_state)
            logger.debug(f"✅ Finished logging state change for {entity_id}")
            
            # Update domain cache by refreshing the entire domain
            # This is less efficient but ensures consistency
            domain = entity_id.split(".")[0]
            await self._refresh_domain_cache(domain)
            
            # Update controllable entities cache if applicable
            if domain in self.controllable_domains:
                await self._refresh_controllable_cache()
            
            logger.debug(f"Updated cache and logged state change for entity {entity_id}")
            
        except Exception as e:
            logger.error(f"Error handling state change for {entity_id}: {e}")
    
    async def _handle_entity_removal(self, entity_id: str, old_state: Dict):
        """Handle removal of an entity from Home Assistant."""
        try:
            # Ensure we have a Redis client
            if not self.redis_client:
                self.redis_client = get_redis_client()
                if not self.redis_client:
                    logger.error("Cannot handle entity removal: Redis client unavailable")
                    return
            
            # Remove from individual entity cache
            entity_key = f"ha:entity:{entity_id}"
            deleted_count = await self.redis_client.delete(entity_key)
            logger.debug(f"🗑️ Deleted entity cache key {entity_key} (deleted: {deleted_count})")
            
            # Log the removal event (with new_state as None to indicate removal)
            await self._log_state_change(entity_id, old_state, None)
            
            # Update domain and controllable caches to remove the entity
            domain = entity_id.split(".")[0]
            await self._refresh_domain_cache(domain)
            
            # Update controllable entities cache if applicable
            if domain in self.controllable_domains:
                await self._refresh_controllable_cache()
            
            logger.info(f"✅ Successfully removed entity {entity_id} from all caches")
            
        except Exception as e:
            logger.error(f"Error handling entity removal for {entity_id}: {e}")
    
    async def _log_state_change(self, entity_id: str, old_state: Dict, new_state: Dict):
        """Log state change to Redis with 7-day TTL."""
        try:
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Create log entry
            log_entry = {
                "timestamp": timestamp,
                "entity_id": entity_id,
                "old_state": old_state,
                "new_state": new_state,
                "state_changed": (old_state.get("state") if old_state else None) != (new_state.get("state") if new_state else None),
                "attributes_changed": (old_state.get("attributes") if old_state else None) != (new_state.get("attributes") if new_state else None),
                "entity_removed": new_state is None
            }
            
            # Use timestamp as score for sorted set (allows chronological ordering)
            timestamp_score = datetime.utcnow().timestamp()
            
            # Store in sorted set for the specific entity (7 days TTL = 604800 seconds)
            log_key = f"ha:log:{entity_id}"
            
            # Add debugging
            logger.debug(f"📝 Logging state change for {entity_id} to Redis key: {log_key}")
            logger.debug(f"Log entry: {json.dumps(log_entry, indent=2)}")
            
            # Add to sorted set with timestamp as score
            await self.redis_client.zadd(log_key, {json.dumps(log_entry): timestamp_score})
            
            # Set TTL on the key (Redis will auto-expire)
            await self.redis_client.expire(log_key, 604800)  # 7 days
            
            # Also maintain a global log for all entities (optional)
            global_log_key = "ha:log:all"
            await self.redis_client.zadd(global_log_key, {json.dumps(log_entry): timestamp_score})
            await self.redis_client.expire(global_log_key, 604800)  # 7 days
            
            # Clean up old entries (keep only last 7 days)
            cutoff_timestamp = timestamp_score - 604800  # 7 days ago
            await self.redis_client.zremrangebyscore(log_key, 0, cutoff_timestamp)
            await self.redis_client.zremrangebyscore(global_log_key, 0, cutoff_timestamp)
            
            logger.debug(f"✅ Successfully logged state change for {entity_id}")
            
        except Exception as e:
            logger.error(f"Error logging state change for {entity_id}: {e}")
    
    async def _refresh_domain_cache(self, domain: str):
        """Refresh the cache for a specific domain."""
        try:
            # Get all entities for this domain from individual caches
            pattern = f"ha:entity:{domain}.*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            
            if not keys:
                return
                
            # Get all entity states for this domain
            domain_entities = []
            for key in keys:
                entity_data = await self.redis_client.get(key)
                if entity_data:
                    try:
                        domain_entities.append(json.loads(entity_data))
                    except json.JSONDecodeError:
                        continue
            
            # Update domain cache
            if domain_entities:
                domain_key = f"ha:domain:{domain}"
                await self.redis_client.setex(domain_key, 3600, json.dumps(domain_entities))
                
        except Exception as e:
            logger.error(f"Error refreshing domain cache for {domain}: {e}")
    
    async def _refresh_controllable_cache(self):
        """Refresh the controllable entities cache."""
        try:
            controllable_entities = []
            
            for domain in self.controllable_domains:
                domain_key = f"ha:domain:{domain}"
                domain_data = await self.redis_client.get(domain_key)
                if domain_data:
                    try:
                        entities = json.loads(domain_data)
                        controllable_entities.extend(entities)
                    except json.JSONDecodeError:
                        continue
            
            if controllable_entities:
                controllable_key = "ha:entities"
                await self.redis_client.setex(
                    controllable_key, 
                    3600, 
                    json.dumps(controllable_entities)
                )
                
        except Exception as e:
            logger.error(f"Error refreshing controllable cache: {e}")
    
    async def _cleanup_stale_cache_entries(self):
        """Remove cache entries for entities that no longer exist in Home Assistant."""
        try:
            # Ensure we have a Redis client
            if not self.redis_client:
                self.redis_client = get_redis_client()
                if not self.redis_client:
                    logger.error("Cannot perform cache cleanup: Redis client unavailable")
                    return
            
            logger.debug("🧹 Starting cache cleanup for removed entities")
            
            # Get all current entities from Home Assistant
            url = f"{self.ha_url}/api/states"
            headers = {"Authorization": f"Bearer {settings.HA_TOKEN}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to get HA states for cleanup: HTTP {response.status}")
                        return
                    
                    current_states = await response.json()
                    current_entity_ids = {state["entity_id"] for state in current_states}
                    logger.debug(f"Current HA entities: {len(current_entity_ids)}")
            
            # Get all cached entities
            pattern = "ha:entity:*"
            cached_keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                cached_keys.append(key)
            
            # Extract entity IDs from cache keys
            cached_entity_ids = {key.decode('utf-8').replace('ha:entity:', '') for key in cached_keys}
            logger.debug(f"Cached entities: {len(cached_entity_ids)}")
            
            # Find stale entities (in cache but not in HA)
            stale_entities = cached_entity_ids - current_entity_ids
            
            if stale_entities:
                logger.info(f"🧹 Found {len(stale_entities)} stale entities to remove from cache")
                
                # Remove stale entities from cache
                for entity_id in stale_entities:
                    entity_key = f"ha:entity:{entity_id}"
                    deleted_count = await self.redis_client.delete(entity_key)
                    logger.debug(f"🗑️ Removed stale entity {entity_id} from cache (deleted: {deleted_count})")
                    
                    # Log the cleanup action
                    log_entry = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "entity_id": entity_id,
                        "old_state": None,  # We don't have the old state for cleanup
                        "new_state": None,
                        "state_changed": True,
                        "attributes_changed": True,
                        "entity_removed": True,
                        "cleanup_action": True
                    }
                    
                    # Add to logs
                    timestamp_score = datetime.utcnow().timestamp()
                    log_key = f"ha:log:{entity_id}"
                    await self.redis_client.zadd(log_key, {json.dumps(log_entry): timestamp_score})
                    await self.redis_client.expire(log_key, 604800)  # 7 days
                
                # Refresh all domain caches to ensure consistency
                domains_to_refresh = {entity_id.split(".")[0] for entity_id in stale_entities}
                for domain in domains_to_refresh:
                    await self._refresh_domain_cache(domain)
                    if domain in self.controllable_domains:
                        await self._refresh_controllable_cache()
                
                logger.info(f"✅ Cache cleanup completed: removed {len(stale_entities)} stale entities")
            else:
                logger.debug("✅ No stale entities found in cache")
                
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")
    
    async def run(self):
        """Main run loop with reconnection logic."""
        logger.info("Starting Home Assistant WebSocket client")
        self.is_running = True
        current_delay = self.reconnect_delay
        
        while self.is_running:
            try:
                # Connect and authenticate
                if await self.connect() and await self.authenticate():
                    current_delay = self.reconnect_delay  # Reset delay on success
                    
                    # Get initial states and subscribe to events
                    if await self.get_initial_states() and await self.subscribe_to_events():
                        logger.info("Home Assistant WebSocket client fully initialized")
                        
                        # Perform periodic cache cleanup (every hour)
                        cleanup_task = asyncio.create_task(self._periodic_cache_cleanup())
                        
                        try:
                            # Listen for events (this blocks until connection is lost)
                            await self.listen_for_events()
                        finally:
                            # Cancel cleanup task when connection is lost
                            cleanup_task.cancel()
                            try:
                                await cleanup_task
                            except asyncio.CancelledError:
                                pass
                    
                # Connection lost, cleanup and retry
                await self.cleanup()
                
                if self.is_running:
                    logger.info(f"Reconnecting in {current_delay} seconds...")
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.max_reconnect_delay)
                    
            except Exception as e:
                logger.error(f"Unexpected error in WebSocket client: {e}")
                await self.cleanup()
                
                if self.is_running:
                    await asyncio.sleep(current_delay)
                    current_delay = min(current_delay * 2, self.max_reconnect_delay)
    
    async def _periodic_cache_cleanup(self):
        """Periodically clean up stale cache entries."""
        while self.is_running:
            try:
                await asyncio.sleep(3600)  # Wait 1 hour
                await self._cleanup_stale_cache_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cache cleanup: {e}")
    
    async def listen_for_events(self):
        """Listen for incoming WebSocket events."""
        if not self.websocket:
            return
            
        try:
            async for message in self.websocket:
                try:
                    # Log raw message to websocket.log only
                    websocket_logger.info(f"🔥 RAW WEBSOCKET MESSAGE: {message}")
                    
                    data = json.loads(message)
                    
                    # Store message for debugging (keep last 10)
                    self.recent_messages.append({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "raw": message[:200] + "..." if len(message) > 200 else message,
                        "parsed": data
                    })
                    if len(self.recent_messages) > 10:
                        self.recent_messages.pop(0)
                    
                    # Log structured data to websocket.log only
                    websocket_logger.info(f"📨 PARSED WEBSOCKET DATA: {json.dumps(data, indent=2)}")
                    
                    # Also log to homeassistant.log
                    logger.info(f"📨 WebSocket message received: {json.dumps(data)}")
                    
                    if data.get("type") == "event":
                        # Get entity_id from the correct nested location
                        entity_id = data.get('event', {}).get('data', {}).get('entity_id', 'unknown')
                        websocket_logger.info(f"🎯 STATE CHANGE EVENT: {entity_id}")
                        logger.info(f"🎯 Processing state change event for: {entity_id}")
                        await self._handle_state_change(data)
                    elif data.get("type") == "result":
                        websocket_logger.info(f"📋 RESULT MESSAGE: {json.dumps(data, indent=2)}")
                        logger.info(f"📋 Received result: {data}")
                    else:
                        websocket_logger.info(f"📬 OTHER MESSAGE TYPE '{data.get('type')}': {json.dumps(data, indent=2)}")
                        logger.info(f"📬 Received other message type: {data.get('type')} - {json.dumps(data)}")
                    
                    websocket_logger.info("=" * 80)  # Separator line
                    
                except json.JSONDecodeError as e:
                    websocket_logger.error(f"❌ JSON DECODE ERROR: {e}")
                    websocket_logger.error(f"❌ RAW MESSAGE: {message}")
                    logger.error(f"Failed to decode WebSocket message: {e}")
                except Exception as e:
                    websocket_logger.error(f"❌ MESSAGE PROCESSING ERROR: {e}")
                    logger.error(f"Error processing WebSocket message: {e}")
                    
        except ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_authenticated = False
        except Exception as e:
            logger.error(f"Error in WebSocket listener: {e}")
            self.is_authenticated = False
    
    async def stop(self):
        """Stop the WebSocket client."""
        logger.info("Stopping Home Assistant WebSocket client")
        self.is_running = False
        await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        self.is_authenticated = False
        
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
            self.websocket = None
        
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass
            self.redis_client = None
    
    def _next_message_id(self) -> int:
        """Get the next message ID for WebSocket communication."""
        current_id = self.message_id
        self.message_id += 1
        return current_id


# Global client instance
_websocket_client = None

async def start_ha_websocket_client():
    """Start the global WebSocket client."""
    global _websocket_client
    
    if _websocket_client and _websocket_client.is_running:
        logger.warning("WebSocket client is already running")
        return
    
    _websocket_client = HomeAssistantWebSocketClient()
    
    # Start the client in the background
    asyncio.create_task(_websocket_client.run())

async def stop_ha_websocket_client():
    """Stop the global WebSocket client."""
    global _websocket_client
    
    if _websocket_client:
        await _websocket_client.stop()
        _websocket_client = None

def get_ha_websocket_client() -> Optional[HomeAssistantWebSocketClient]:
    """Get the global WebSocket client instance."""
    return _websocket_client