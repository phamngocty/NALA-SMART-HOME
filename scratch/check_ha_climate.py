import sys
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8')

resp2 = httpx.get("http://192.168.1.114:8765/api/ha/entities")
if resp2.status_code == 200:
    data = resp2.json()
    entities = data if isinstance(data, list) else data.get("entities", [])
    climate_entities = [e for e in entities if e.get("entity_id", "").startswith("climate")]
    print(f"Found {len(climate_entities)} climate entities:")
    for c in climate_entities:
        print(f"ID: {c.get('entity_id')}, State: {c.get('state')}, Name: {c.get('name') or c.get('attributes', {}).get('friendly_name')}")
        print("Attributes:", json.dumps(c.get('attributes', {}), ensure_ascii=False, indent=2))
