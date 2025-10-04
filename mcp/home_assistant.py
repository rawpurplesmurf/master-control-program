import httpx
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

from mcp.config import settings
from mcp.database import SessionLocal
from mcp.models import Entity

async def poll_home_assistant():
    """Polls Home Assistant for all entities and updates the database."""
    headers = {"Authorization": f"Bearer {settings.HA_TOKEN}", "Content-Type": "application/json"}
    print("Polling Home Assistant for entities...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.HA_URL}/api/states", headers=headers, timeout=30)
            response.raise_for_status()
            entities = response.json()

        db = SessionLocal()
        try:
            for entity_data in entities:
                entity_id = entity_data['entity_id']
                friendly_name = entity_data['attributes'].get('friendly_name', entity_id.split('.')[1].replace('_', ' '))
                domain = entity_id.split('.')[0]
                last_updated_str = entity_data['last_updated']
                # Ensure timezone info is handled correctly for fromisoformat
                if last_updated_str.endswith('Z'):
                    last_updated_str = last_updated_str[:-1] + '+00:00'
                last_updated = datetime.fromisoformat(last_updated_str)

                db.merge(Entity(
                    entity_id=entity_id,
                    friendly_name=friendly_name,
                    domain=domain,
                    last_updated=last_updated
                ))
            db.commit()
            print(f"Successfully polled and updated/merged {len(entities)} entities.")
        except SQLAlchemyError as e:
            print(f"Database error during polling: {e}")
            db.rollback()
        finally:
            db.close()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error polling Home Assistant: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"An unexpected error occurred during polling: {e}")