import sys
import httpx
import unicodedata
import re

sys.stdout.reconfigure(encoding='utf-8')

resp = httpx.get("http://192.168.1.114:8765/api/ha/entities")
entities = resp.json()

def remove_accents(input_str):
    if not input_str:
        return ""
    s1 = unicodedata.normalize('NFD', input_str)
    s2 = "".join(c for c in s1 if unicodedata.category(c) != 'Mn')
    s2 = s2.replace('đ', 'd').replace('Đ', 'D')
    return s2.lower()

def resolve_entity_id(raw_eid, entities, target_domain="climate"):
    # 1. Direct match
    for e in entities:
        if e.get("entity_id") == raw_eid:
            return e.get("entity_id"), e.get("attributes", {}).get("friendly_name") or e.get("name")

    # 2. Fuzzy match by keywords in entity_id, friendly_name, or area_name
    clean_query = remove_accents(raw_eid.replace(".", " ").replace("_", " "))
    tokens = [t for t in re.split(r'\s+', clean_query) if len(t) > 1 and t not in ["climate", "light", "switch", "fan"]]

    best_match = None
    best_score = 0

    for e in entities:
        dom = e.get("domain") or e.get("entity_id", "").split(".")[0]
        if target_domain and dom != target_domain:
            continue
        
        name = e.get("name") or e.get("attributes", {}).get("friendly_name") or ""
        area = e.get("area_name") or ""
        target_str = remove_accents(f"{e.get('entity_id')} {name} {area}")

        score = sum(1 for t in tokens if t in target_str)
        if score > best_score:
            best_score = score
            best_match = e

    if best_match and best_score >= 1:
        fname = best_match.get("attributes", {}).get("friendly_name") or best_match.get("name") or best_match.get("entity_id")
        return best_match.get("entity_id"), fname

    return raw_eid, raw_eid

# Test resolve for the user's hallucinated / spoken ID
raw_input = "climate.may_lanh_phong_ngu_ty"
resolved_id, friendly_name = resolve_entity_id(raw_input, entities, "climate")
print(f"Resolving '{raw_input}':")
print(f" -> Real Entity ID: {resolved_id}")
print(f" -> Friendly Name : {friendly_name}")

assert resolved_id == "climate.150633094640317_climate", "Must match real Midea AC entity!"
print("Test PASSED 100%!")
