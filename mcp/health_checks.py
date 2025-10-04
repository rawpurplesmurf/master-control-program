import httpx
import redis

from mcp.config import settings
from mcp.database import engine

def check_mysql_connection():
    """Checks the connection to the MySQL database."""
    status = "OK"
    try:
        connection = engine.connect()
        connection.close()
    except Exception as e:
        status = f"FAILED ({e})"
    except Exception as e:
        status = f"FAILED (An unexpected error occurred: {e})"
    print(f"  - MySQL Connection ({settings.MYSQL_HOST}): {status}")

async def check_home_assistant_connection():
    """Checks the connection to the Home Assistant API."""
    status = "OK"
    headers = {"Authorization": f"Bearer {settings.HA_TOKEN}"}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.HA_URL}/api/", headers=headers, timeout=10)
            response.raise_for_status()
            if response.json().get("message") != "API running.":
                status = "FAILED (Unexpected API response)"
    except httpx.HTTPStatusError as e:
        status = f"FAILED (HTTP {e.response.status_code})"
    except Exception as e:
        status = f"FAILED ({e})"
    print(f"  - Home Assistant Connection ({settings.HA_URL}): {status}")

async def check_ollama_connection():
    """Checks the connection to the Ollama server."""
    status = "OK"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.OLLAMA_URL, timeout=10)
            # A 200 OK with "Ollama is running" is a success
            if response.status_code != 200:
                 status = f"FAILED (HTTP {response.status_code})"
    except Exception as e:
        status = f"FAILED ({e})"
    print(f"  - Ollama Connection ({settings.OLLAMA_URL}): {status}")

async def check_redis_connection():
    """Checks the connection to the Redis server."""
    status = "OK"
    try:
        # Use the global async client
        from mcp.cache import redis_client
        await redis_client.ping()
    except Exception as e:
        status = f"FAILED ({e})"
    print(f"  - Redis Connection ({settings.REDIS_HOST}:{settings.REDIS_PORT}): {status}")