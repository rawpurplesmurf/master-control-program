from dotenv import load_dotenv
import os
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
import time
import requests
import redis
import os
import json


HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "your_long_lived_access_token")

# Prefer REDIS_URL, but support REDIS_HOST/REDIS_PORT for compatibility
REDIS_URL = os.environ.get("REDIS_URL")
if not REDIS_URL:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = os.environ.get("REDIS_PORT", "6379")
    REDIS_URL = f"redis://{host}:{port}/0"

CONTROL_DOMAINS = {"switch", "light", "climate", "fan", "cover", "media_player"}

def get_redis_client():
    return redis.Redis.from_url(REDIS_URL)

def get_ha_headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

def poll_and_cache_entities():
    print("Polling Home Assistant for entity states...")
    resp = requests.get(f"{HA_URL}/api/states", headers=get_ha_headers(), timeout=10)
    resp.raise_for_status()
    all_entities = resp.json()
    print(f"Fetched {len(all_entities)} entities from Home Assistant.")
    controllable = [
        e for e in all_entities
        if e["entity_id"].split(".")[0] in CONTROL_DOMAINS
    ]
    print(f"Found {len(controllable)} controllable entities. Writing to Redis...")
    r = get_redis_client()
    r.set("ha:entities", json.dumps(controllable))
    print("Controllable entities cached in Redis as 'ha:entities'.")

def main():
    print("Starting Home Assistant poller. Will poll every 60 seconds.")
    while True:
        try:
            poll_and_cache_entities()
        except Exception as e:
            print(f"Polling error: {e}")
        print("Sleeping for 60 seconds.\n")
        time.sleep(60)

if __name__ == "__main__":
    main()
