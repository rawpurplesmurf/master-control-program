import redis.asyncio as redis
from mcp.config import settings

def get_redis_client():
    """
    Returns an asynchronous Redis client.
    """
    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

# Global Redis client instance
redis_client = get_redis_client()
