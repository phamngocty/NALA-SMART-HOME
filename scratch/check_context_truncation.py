import sys
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8')

resp = httpx.get("http://192.168.1.114:8765/api/ha/entities")
entities = resp.json()
print("Total entities in HA:", len(entities))

lines = []
for e in entities:
    domain = e.get("domain", "") or e.get("entity_id", "").split(".")[0]
    if domain in ["light", "switch", "climate", "fan", "cover", "scene"]:
        eid = e.get("entity_id", "")
        name = e.get("name") or e.get("attributes", {}).get("friendly_name") or eid
        area = e.get("area_name", "Chung")
        state = e.get("state", "off")
        lines.append(f"- {name} ({eid}) | Phòng: {area} | Trạng thái: {state}")

print(f"Total matching controllable entities: {len(lines)}")
first_50 = "\n".join(lines[:50])
print("Is climate in first 50?", "climate." in first_50)
if "climate." not in first_50:
    print("WARNING: Climate entities were truncated because they are after index 50!")
    for idx, l in enumerate(lines):
        if "climate." in l:
            print(f"  Found climate at index {idx}: {l}")
