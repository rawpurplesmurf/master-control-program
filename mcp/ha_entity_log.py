"""
Home Assistant Entity Log Manager
Provides functions to retrieve and manage HA entity state change logs from Redis.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from mcp.cache import get_redis_client

logger = logging.getLogger(__name__)

async def get_entity_log(
    entity_id: str, 
    limit: int = 100, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get state change log for a specific entity.
    
    Args:
        entity_id: The Home Assistant entity ID (e.g., "light.living_room")
        limit: Maximum number of log entries to return (default: 100)
        start_date: ISO format date string for range start (optional)
        end_date: ISO format date string for range end (optional)
    
    Returns:
        List of log entries sorted by timestamp (newest first)
    """
    try:
        redis_client = get_redis_client()
        log_key = f"ha:log:{entity_id}"
        
        # Calculate score range for date filtering
        max_score = "+inf"
        min_score = "-inf"
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                max_score = end_dt.timestamp()
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                min_score = start_dt.timestamp()
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
        
        # Get log entries from Redis sorted set (newest first)
        log_entries = await redis_client.zrevrangebyscore(
            log_key, 
            max_score, 
            min_score, 
            start=0, 
            num=limit
        )
        
        # Parse JSON entries
        parsed_entries = []
        for entry in log_entries:
            try:
                parsed_entry = json.loads(entry)
                parsed_entries.append(parsed_entry)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse log entry: {e}")
                continue
        
        logger.debug(f"Retrieved {len(parsed_entries)} log entries for {entity_id}")
        return parsed_entries
        
    except Exception as e:
        logger.error(f"Error retrieving entity log for {entity_id}: {e}")
        return []

async def get_entity_log_summary(entity_id: str, days: int = 7) -> Dict[str, Any]:
    """
    Get summary statistics for an entity's state changes over the specified period.
    
    Args:
        entity_id: The Home Assistant entity ID
        days: Number of days to look back (default: 7)
    
    Returns:
        Dictionary with summary statistics
    """
    try:
        # Get log entries for the specified period
        start_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        log_entries = await get_entity_log(entity_id, limit=1000, start_date=start_date)
        
        if not log_entries:
            return {
                "entity_id": entity_id,
                "period_days": days,
                "total_changes": 0,
                "state_changes": 0,
                "attribute_changes": 0,
                "most_recent_change": None,
                "change_frequency_per_day": 0.0
            }
        
        # Calculate statistics
        total_changes = len(log_entries)
        state_changes = sum(1 for entry in log_entries if entry.get("state_changed", False))
        attribute_changes = sum(1 for entry in log_entries if entry.get("attributes_changed", False))
        
        most_recent_change = log_entries[0] if log_entries else None
        change_frequency = total_changes / days if days > 0 else 0.0
        
        return {
            "entity_id": entity_id,
            "period_days": days,
            "total_changes": total_changes,
            "state_changes": state_changes,
            "attribute_changes": attribute_changes,
            "most_recent_change": most_recent_change,
            "change_frequency_per_day": round(change_frequency, 2)
        }
        
    except Exception as e:
        logger.error(f"Error getting entity log summary for {entity_id}: {e}")
        return {
            "entity_id": entity_id,
            "period_days": days,
            "total_changes": 0,
            "state_changes": 0,
            "attribute_changes": 0,
            "most_recent_change": None,
            "change_frequency_per_day": 0.0,
            "error": str(e)
        }

async def get_all_logged_entities() -> List[str]:
    """
    Get list of all entities that have log entries.
    
    Returns:
        List of entity IDs that have logs
    """
    try:
        redis_client = get_redis_client()
        
        # Find all log keys
        log_keys = await redis_client.keys("ha:log:*")
        
        # Extract entity IDs (exclude the global log)
        entity_ids = []
        for key in log_keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            
            if key == "ha:log:all":
                continue
                
            # Extract entity ID from key (format: ha:log:domain.entity)
            if key.startswith("ha:log:"):
                entity_id = key[7:]  # Remove "ha:log:" prefix
                entity_ids.append(entity_id)
        
        return sorted(entity_ids)
        
    except Exception as e:
        logger.error(f"Error getting logged entities: {e}")
        return []

async def cleanup_old_logs(days_to_keep: int = 7):
    """
    Clean up log entries older than specified days.
    
    Args:
        days_to_keep: Number of days of logs to retain
    """
    try:
        redis_client = get_redis_client()
        cutoff_timestamp = (datetime.utcnow() - timedelta(days=days_to_keep)).timestamp()
        
        # Get all log keys
        log_keys = await redis_client.keys("ha:log:*")
        
        cleaned_count = 0
        for key in log_keys:
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            
            # Remove old entries
            removed_count = await redis_client.zremrangebyscore(key, 0, cutoff_timestamp)
            cleaned_count += removed_count
        
        logger.info(f"Cleaned up {cleaned_count} old log entries older than {days_to_keep} days")
        return cleaned_count
        
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        return 0