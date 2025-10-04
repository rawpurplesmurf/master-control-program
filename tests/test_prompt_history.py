import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from mcp.prompt_history import PromptHistoryManager


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('mcp.prompt_history.redis_client') as mock_client:
        # Configure the mock to return proper values
        mock_client.setex = AsyncMock()
        mock_client.zadd = AsyncMock()
        mock_client.zrevrange = AsyncMock()
        mock_client.get = AsyncMock()
        mock_client.zcard = AsyncMock()
        mock_client.delete = AsyncMock()
        mock_client.zrem = AsyncMock()
        yield mock_client


@pytest.fixture
def prompt_history_manager():
    """Create a PromptHistoryManager instance for testing."""
    return PromptHistoryManager()


class TestPromptHistoryManager:
    
    @pytest.mark.asyncio
    async def test_store_prompt_interaction(self, prompt_history_manager, mock_redis):
        """Test storing a prompt interaction."""
        # Arrange
        prompt = "System: You are helpful\nUser: What time is it?"
        response = "The current time is 2:30 PM"
        source = "api"
        metadata = {"template_used": "default", "processing_time_ms": 1500}
        
        # Act
        interaction_id = await prompt_history_manager.store_prompt_interaction(
            prompt, response, source, metadata
        )
        
        # Assert
        assert interaction_id is not None
        assert len(interaction_id) > 0
        
        # Verify Redis calls
        mock_redis.setex.assert_called_once()
        mock_redis.zadd.assert_called_once()
        
        # Check the stored data structure
        setex_call_args = mock_redis.setex.call_args[0]
        stored_key = setex_call_args[0]
        stored_data = json.loads(setex_call_args[2])
        
        assert stored_key.startswith("mcp:prompt_history:")
        assert stored_data["prompt"] == prompt
        assert stored_data["response"] == response
        assert stored_data["source"] == source
        assert stored_data["metadata"] == metadata
        assert "timestamp" in stored_data
        assert "id" in stored_data

    @pytest.mark.asyncio
    async def test_get_prompt_history(self, prompt_history_manager, mock_redis):
        """Test retrieving prompt history."""
        # Arrange
        interaction_id = "1696345678000"
        mock_interaction_data = {
            "id": interaction_id,
            "prompt": "Test prompt",
            "response": "Test response", 
            "source": "api",
            "timestamp": "2023-10-03T12:34:56+00:00",
            "metadata": {"test": "data"}
        }
        
        mock_redis.zrevrange.return_value = [interaction_id]
        mock_redis.get.return_value = json.dumps(mock_interaction_data).encode('utf-8')
        
        # Act
        interactions = await prompt_history_manager.get_prompt_history(limit=10)
        
        # Assert
        assert len(interactions) == 1
        assert interactions[0]["id"] == interaction_id
        assert interactions[0]["prompt"] == "Test prompt"
        assert interactions[0]["source"] == "api"
        
        mock_redis.zrevrange.assert_called_once()
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_prompt_history_with_source_filter(self, prompt_history_manager, mock_redis):
        """Test retrieving prompt history with source filtering."""
        # Arrange
        api_interaction = {
            "id": "1",
            "prompt": "API prompt",
            "response": "API response",
            "source": "api",
            "timestamp": "2023-10-03T12:34:56+00:00",
            "metadata": {}
        }
        
        skippy_interaction = {
            "id": "2", 
            "prompt": "Skippy prompt",
            "response": "Skippy response",
            "source": "skippy",
            "timestamp": "2023-10-03T12:35:56+00:00",
            "metadata": {}
        }
        
        mock_redis.zrevrange.return_value = ["1", "2"]
        mock_redis.get.side_effect = [
            json.dumps(api_interaction).encode('utf-8'),
            json.dumps(skippy_interaction).encode('utf-8')
        ]
        
        # Act - Filter by 'api' source
        interactions = await prompt_history_manager.get_prompt_history(
            limit=10, 
            source_filter="api"
        )
        
        # Assert
        assert len(interactions) == 1
        assert interactions[0]["source"] == "api"
        assert interactions[0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_get_prompt_interaction(self, prompt_history_manager, mock_redis):
        """Test retrieving a specific prompt interaction."""
        # Arrange
        interaction_id = "1696345678000"
        mock_interaction_data = {
            "id": interaction_id,
            "prompt": "Specific test prompt",
            "response": "Specific test response",
            "source": "manual", 
            "timestamp": "2023-10-03T12:34:56+00:00",
            "metadata": {"specific": True}
        }
        
        mock_redis.get.return_value = json.dumps(mock_interaction_data).encode('utf-8')
        
        # Act
        interaction = await prompt_history_manager.get_prompt_interaction(interaction_id)
        
        # Assert
        assert interaction is not None
        assert interaction["id"] == interaction_id
        assert interaction["prompt"] == "Specific test prompt"
        assert interaction["source"] == "manual"
        
        mock_redis.get.assert_called_once_with(f"mcp:prompt_history:{interaction_id}")

    @pytest.mark.asyncio
    async def test_get_prompt_interaction_not_found(self, prompt_history_manager, mock_redis):
        """Test retrieving a non-existent prompt interaction."""
        # Arrange
        mock_redis.get.return_value = None
        
        # Act
        interaction = await prompt_history_manager.get_prompt_interaction("nonexistent")
        
        # Assert
        assert interaction is None

    @pytest.mark.asyncio
    async def test_delete_prompt_interaction(self, prompt_history_manager, mock_redis):
        """Test deleting a prompt interaction."""
        # Arrange
        interaction_id = "1696345678000"
        mock_redis.delete.return_value = 1
        mock_redis.zrem.return_value = 1
        
        # Act
        deleted = await prompt_history_manager.delete_prompt_interaction(interaction_id)
        
        # Assert
        assert deleted is True
        
        mock_redis.delete.assert_called_once_with(f"mcp:prompt_history:{interaction_id}")
        mock_redis.zrem.assert_called_once_with("mcp:prompt_history:timeline", interaction_id)

    @pytest.mark.asyncio
    async def test_delete_prompt_interaction_not_found(self, prompt_history_manager, mock_redis):
        """Test deleting a non-existent prompt interaction."""
        # Arrange
        mock_redis.delete.return_value = 0
        mock_redis.zrem.return_value = 0
        
        # Act
        deleted = await prompt_history_manager.delete_prompt_interaction("nonexistent")
        
        # Assert
        assert deleted is False

    @pytest.mark.asyncio
    async def test_get_history_stats(self, prompt_history_manager, mock_redis):
        """Test getting prompt history statistics."""
        # Arrange
        mock_redis.zcard.return_value = 150
        mock_redis.zrevrange.return_value = ["1", "2", "3"]
        
        # Mock interactions with different sources
        interactions_data = [
            {"source": "api", "id": "1"}, 
            {"source": "api", "id": "2"},
            {"source": "skippy", "id": "3"}
        ]
        
        mock_redis.get.side_effect = [
            json.dumps(data).encode('utf-8') for data in interactions_data
        ]
        
        # Act
        stats = await prompt_history_manager.get_history_stats()
        
        # Assert
        assert stats["total_interactions"] == 150
        assert stats["source_distribution"]["api"] == 2
        assert stats["source_distribution"]["skippy"] == 1
        assert stats["recent_count"] == 3

    @pytest.mark.asyncio
    async def test_rerun_prompt_interaction(self, prompt_history_manager, mock_redis):
        """Test re-running a prompt interaction."""
        # Arrange
        original_id = "1696345678000"
        original_interaction = {
            "id": original_id,
            "prompt": "What is 2+2?",
            "response": "2+2 equals 4",
            "source": "api",
            "timestamp": "2023-10-03T12:34:56+00:00",
            "metadata": {"template_used": "math"}
        }
        
        mock_redis.get.return_value = json.dumps(original_interaction).encode('utf-8')
        mock_redis.setex = AsyncMock()
        mock_redis.zadd = AsyncMock()
        
        # Mock the Ollama call
        with patch('mcp.prompt_history.call_ollama_text') as mock_ollama:
            mock_ollama.return_value = "2+2 equals 4 (rerun response)"
            
            # Act
            result = await prompt_history_manager.rerun_prompt_interaction(original_id)
        
        # Assert
        assert result["success"] is True
        assert "new_interaction_id" in result
        assert result["original_interaction_id"] == original_id
        assert result["response"] == "2+2 equals 4 (rerun response)"
        assert "processing_time_ms" in result
        
        # Verify new interaction was stored
        mock_redis.setex.assert_called_once()
        mock_redis.zadd.assert_called_once()

    @pytest.mark.asyncio 
    async def test_rerun_prompt_interaction_not_found(self, prompt_history_manager, mock_redis):
        """Test re-running a non-existent prompt interaction."""
        # Arrange
        mock_redis.get.return_value = None
        
        # Act
        result = await prompt_history_manager.rerun_prompt_interaction("nonexistent")
        
        # Assert
        assert "error" in result
        assert result["error"] == "Original interaction not found"

    @pytest.mark.asyncio
    async def test_store_prompt_interaction_error_handling(self, prompt_history_manager, mock_redis):
        """Test error handling in store_prompt_interaction."""
        # Arrange
        mock_redis.setex.side_effect = Exception("Redis error")
        
        # Act & Assert
        with pytest.raises(Exception, match="Redis error"):
            await prompt_history_manager.store_prompt_interaction(
                "test prompt", 
                "test response", 
                "api"
            )

    @pytest.mark.asyncio
    async def test_get_prompt_history_error_handling(self, prompt_history_manager, mock_redis):
        """Test error handling in get_prompt_history."""
        # Arrange
        mock_redis.zrevrange.side_effect = Exception("Redis error")
        
        # Act
        interactions = await prompt_history_manager.get_prompt_history()
        
        # Assert - Should return empty list on error
        assert interactions == []

    @pytest.mark.asyncio
    async def test_pagination(self, prompt_history_manager, mock_redis):
        """Test pagination in get_prompt_history."""
        # Arrange
        limit = 50
        offset = 100
        mock_redis.zrevrange.return_value = []
        
        # Act
        await prompt_history_manager.get_prompt_history(limit=limit, offset=offset)
        
        # Assert - Check that zrevrange was called with correct pagination params
        mock_redis.zrevrange.assert_called_once_with(
            "mcp:prompt_history:timeline",
            offset,
            offset + limit - 1
        )