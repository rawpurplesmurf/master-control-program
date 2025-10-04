"""
Prompt History Management for Master Control Program.

This module handles storage and retrieval of all LLM interactions including:
- Prompts sent to the LLM
- Responses received from the LLM  
- Metadata (timestamp, source, processing time)
- Re-execution capabilities
"""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from mcp.cache import redis_client

logger = logging.getLogger(__name__)

class PromptHistoryManager:
    def __init__(self):
        self.history_key_prefix = "mcp:prompt_history"
        
    async def store_prompt_interaction(
        self, 
        prompt: str, 
        response: str, 
        source: str = "api",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a prompt/response interaction in Redis.
        
        Args:
            prompt: The full prompt sent to the LLM
            response: The response received from the LLM
            source: Source of the interaction (skippy, submind, api, manual)
            metadata: Additional metadata (processing_time, template_used, etc.)
            
        Returns:
            The interaction ID for future reference
        """
        try:
            # Generate unique interaction ID
            timestamp = datetime.now(timezone.utc)
            interaction_id = f"{int(timestamp.timestamp() * 1000)}"
            
            # Prepare interaction data
            interaction_data = {
                "id": interaction_id,
                "prompt": prompt,
                "response": response,
                "source": source,
                "timestamp": timestamp.isoformat(),
                "metadata": metadata or {}
            }
            
            # Store individual interaction
            key = f"{self.history_key_prefix}:{interaction_id}"
            await redis_client.setex(key, 86400 * 30, json.dumps(interaction_data))  # 30 days retention
            
            # Add to sorted set for chronological retrieval
            await redis_client.zadd(f"{self.history_key_prefix}:timeline", {interaction_id: timestamp.timestamp()})
            
            logger.info(f"Stored prompt interaction {interaction_id} from source: {source}")
            return interaction_id
            
        except Exception as e:
            logger.error(f"Error storing prompt interaction: {str(e)}")
            raise
    
    async def get_prompt_history(
        self, 
        limit: int = 100, 
        offset: int = 0, 
        source_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve prompt history with optional filtering.
        
        Args:
            limit: Maximum number of interactions to return
            offset: Number of interactions to skip (for pagination)
            source_filter: Filter by source (skippy, submind, api, manual)
            
        Returns:
            List of interaction dictionaries sorted by timestamp (newest first)
        """
        try:
            # Get interaction IDs from timeline (newest first)
            interaction_ids = await redis_client.zrevrange(
                f"{self.history_key_prefix}:timeline", 
                offset, 
                offset + limit - 1
            )
            
            interactions = []
            for interaction_id in interaction_ids:
                # Decode bytes if necessary
                if isinstance(interaction_id, bytes):
                    interaction_id = interaction_id.decode('utf-8')
                    
                key = f"{self.history_key_prefix}:{interaction_id}"
                data = await redis_client.get(key)
                
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    interaction = json.loads(data)
                    
                    # Apply source filter if specified
                    if source_filter and interaction.get("source") != source_filter:
                        continue
                        
                    interactions.append(interaction)
            
            logger.info(f"Retrieved {len(interactions)} prompt history interactions")
            return interactions
            
        except Exception as e:
            logger.error(f"Error retrieving prompt history: {str(e)}")
            return []
    
    async def get_prompt_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific prompt interaction by ID.
        
        Args:
            interaction_id: The interaction ID to retrieve
            
        Returns:
            Interaction dictionary or None if not found
        """
        try:
            key = f"{self.history_key_prefix}:{interaction_id}"
            data = await redis_client.get(key)
            
            if data:
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                interaction = json.loads(data)
                logger.info(f"Retrieved prompt interaction: {interaction_id}")
                return interaction
            
            logger.warning(f"Prompt interaction not found: {interaction_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving prompt interaction {interaction_id}: {str(e)}")
            return None
    
    async def delete_prompt_interaction(self, interaction_id: str) -> bool:
        """
        Delete a specific prompt interaction.
        
        Args:
            interaction_id: The interaction ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Remove from individual storage
            key = f"{self.history_key_prefix}:{interaction_id}"
            deleted_individual = await redis_client.delete(key)
            
            # Remove from timeline
            deleted_timeline = await redis_client.zrem(f"{self.history_key_prefix}:timeline", interaction_id)
            
            if deleted_individual or deleted_timeline:
                logger.info(f"Deleted prompt interaction: {interaction_id}")
                return True
            
            logger.warning(f"Prompt interaction not found for deletion: {interaction_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting prompt interaction {interaction_id}: {str(e)}")
            return False
    
    async def get_history_stats(self) -> Dict[str, Any]:
        """
        Get statistics about prompt history.
        
        Returns:
            Dictionary with history statistics
        """
        try:
            total_count = await redis_client.zcard(f"{self.history_key_prefix}:timeline")
            
            # Get recent interactions to calculate source distribution
            recent_ids = await redis_client.zrevrange(f"{self.history_key_prefix}:timeline", 0, 99)
            source_counts = {}
            
            for interaction_id in recent_ids:
                # Decode bytes if necessary
                if isinstance(interaction_id, bytes):
                    interaction_id = interaction_id.decode('utf-8')
                    
                key = f"{self.history_key_prefix}:{interaction_id}"
                data = await redis_client.get(key)
                
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    interaction = json.loads(data)
                    source = interaction.get("source", "unknown")
                    source_counts[source] = source_counts.get(source, 0) + 1
            
            return {
                "total_interactions": total_count,
                "source_distribution": source_counts,
                "recent_count": len(recent_ids)
            }
            
        except Exception as e:
            logger.error(f"Error getting history stats: {str(e)}")
            return {"total_interactions": 0, "source_distribution": {}, "recent_count": 0}

    async def rerun_prompt_interaction(self, interaction_id: str) -> Dict[str, Any]:
        """
        Re-run a previous prompt interaction with the same prompt.
        
        Args:
            interaction_id: The interaction ID to re-run
            
        Returns:
            New interaction result or error dict
        """
        try:
            # Get original interaction
            original = await self.get_prompt_interaction(interaction_id)
            if not original:
                return {"error": "Original interaction not found"}
            
            # Extract original prompt
            original_prompt = original.get("prompt", "")
            if not original_prompt:
                return {"error": "No prompt found in original interaction"}
            
            # Re-run the prompt using Ollama
            from mcp.ollama import call_ollama_text
            start_time = datetime.now()
            
            new_response = await call_ollama_text(original_prompt)
            
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Store new interaction
            new_metadata = {
                "rerun_of": interaction_id,
                "processing_time_ms": processing_time,
                "original_source": original.get("source", "unknown")
            }
            
            new_interaction_id = await self.store_prompt_interaction(
                prompt=original_prompt,
                response=new_response,
                source="rerun",
                metadata=new_metadata
            )
            
            return {
                "success": True,
                "new_interaction_id": new_interaction_id,
                "original_interaction_id": interaction_id,
                "response": new_response,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            logger.error(f"Error re-running prompt interaction {interaction_id}: {str(e)}")
            return {"error": f"Failed to re-run interaction: {str(e)}"}

# Global instance
prompt_history_manager = PromptHistoryManager()