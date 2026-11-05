import os
import sys
import json
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

# Fetch real data from NAS Hub
res_ent = urllib.request.urlopen('http://192.168.1.114:8765/api/ha/entities', timeout=5)
entities = json.loads(res_ent.read().decode('utf-8'))

res_areas = urllib.request.urlopen('http://192.168.1.114:8765/api/ha/areas', timeout=5)
areas_data = json.loads(res_areas.read().decode('utf-8'))
areas = areas_data.get('areas', [])
floors = areas_data.get('floors', [])

# Map floor names to friendly display
DEFAULT_FLOOR_ORDER = [
    {"floor_id": "tret", "floor_name": "Tầng Trệt", "level": 0},
    {"floor_id": "tang1", "floor_name": "Tầng 1", "level": 1},
    {"floor_id": "tang2", "floor_name": "Tầng 2", "level": 2},
    {"floor_id": "tang_3", "floor_name": "Tầng 3", "level": 3},
    {"floor_id": "other", "floor_name": "Khu Vực Khác", "level": 99}
]

floor_map = {}
for f in DEFAULT_FLOOR_ORDER:
    floor_map[f["floor_id"]] = f["floor_name"]
for f in floors:
    fid = f.get("floor_id")
    if fid:
        fname = f.get("name", fid)
        if fid == "tret": fname = "Tầng Trệt"
        elif fid == "tang1": fname = "Tầng 1"
        elif fid == "tang2": fname = "Tầng 2"
        elif fid == "tang_3": fname = "Tầng 3"
        floor_map[fid] = fname

# Group entities by area_id
entities_by_area = {}
for e in entities:
    aid = e.get("area_id") or "other"
    st = e.get("state", "off")
    domain = e.get("domain", "")
    is_on = (st in ["on", "true", "open"]) or (domain == "climate" and st not in ["off", "unavailable", "unknown", ""])
    e_copy = {
        "entity_id": e.get("entity_id"),
        "name": e.get("name") or e.get("entity_id"),
        "domain": domain,
        "state": st,
        "is_on": is_on
    }
    entities_by_area.setdefault(aid, []).append(e_copy)

# Group areas by floor_id
areas_by_floor = {}
for a in areas:
    aid = a.get("area_id")
    fid = a.get("floor_id") or "other"
    aname = a.get("name", aid)
    a_ents = entities_by_area.get(aid, [])
    active_in_area = sum(1 for item in a_ents if item["is_on"])
    area_obj = {
        "area_id": aid,
        "name": aname,
        "icon": a.get("icon") or "mdi:home-outline",
        "active_count": active_in_area,
        "total_count": len(a_ents),
        "entities": a_ents
    }
    areas_by_floor.setdefault(fid, []).append(area_obj)

# Build result floors list
result_floors = []
for f_def in DEFAULT_FLOOR_ORDER:
    fid = f_def["floor_id"]
    fname = floor_map.get(fid, f_def["floor_name"])
    f_areas = areas_by_floor.get(fid, [])
    # Sort rooms alphabetically or active first
    f_areas.sort(key=lambda x: (0 if x["active_count"] > 0 else 1, x["name"]))
    total_active_floor = sum(ar["active_count"] for ar in f_areas)
    total_ents_floor = sum(ar["total_count"] for ar in f_areas)
    result_floors.append({
        "floor_id": fid,
        "floor_name": fname,
        "level": f_def["level"],
        "active_count": total_active_floor,
        "total_count": total_ents_floor,
        "areas": f_areas
    })

print(json.dumps(result_floors, indent=2, ensure_ascii=False))
