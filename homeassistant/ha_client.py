from dotenv import load_dotenv
load_dotenv()
import requests
import os

HA_URL = os.environ.get("HA_URL", "http://localhost:8123")
HA_TOKEN = os.environ.get("HA_TOKEN", "your_long_lived_access_token")

def get_ha_headers():
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }

def call_service(domain: str, service: str, data: dict):
    url = f"{HA_URL}/api/services/{domain}/{service}"
    resp = requests.post(url, headers=get_ha_headers(), json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()
