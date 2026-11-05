import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://192.168.1.114:8765"

print("1. Testing GET /api/all-house/config...")
try:
    req = urllib.request.Request(f"{BASE_URL}/api/all-house/config")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("Status code:", resp.status)
        data = json.loads(resp.read().decode('utf-8'))
        print("Response data:")
        print("Config:", json.dumps(data.get("config"), indent=2, ensure_ascii=False))
        print("House Status:", json.dumps(data.get("house_status"), indent=2, ensure_ascii=False))
        print(f"Discovered {len(data.get('scenes', []))} Scenes from Home Assistant.")
        if data.get('scenes'):
            for sc in data.get('scenes')[:5]:
                print(f" - {sc.get('friendly_name')} ({sc.get('entity_id')})")
except Exception as e:
    print("GET /api/all-house/config failed:", e)

print("\n2. Testing POST /api/all-house/config...")
try:
    update_payload = {
        "enabled": True,
        "action_mode": "turn_off_selected",
        "controlled_domains": ["light", "fan"],
        "include_climate": False,
        "include_switch": False,
        "excluded_entities": [],
        "scene_entity_id": "",
        "confirm_prompt": False,
        "alert_title": "TOÀN BỘ NHÀ"
    }
    req2 = urllib.request.Request(
        f"{BASE_URL}/api/all-house/config",
        data=json.dumps(update_payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req2, timeout=5) as resp2:
        print("Status code:", resp2.status)
        data2 = json.loads(resp2.read().decode('utf-8'))
        print("POST response:", json.dumps(data2, indent=2, ensure_ascii=False))
except Exception as e:
    print("POST /api/all-house/config failed:", e)

print("\n3. Testing GET /admin contains allHouseConfigModal and allHouseStrip...")
try:
    req3 = urllib.request.Request(f"{BASE_URL}/admin")
    with urllib.request.urlopen(req3, timeout=5) as resp3:
        html = resp3.read().decode('utf-8')
        has_strip = "allHouseStrip" in html
        has_modal = "allHouseConfigModal" in html
        has_btn = "btn-allhouse-header" in html
        print(f"Contains allHouseStrip: {has_strip}")
        print(f"Contains allHouseConfigModal: {has_modal}")
        print(f"Contains btn-allhouse-header: {has_btn}")
        assert has_strip and has_modal and has_btn, "UI elements missing in /admin!"
        print("✓ All UI components verified in live Web Admin!")
except Exception as e:
    print("GET /admin check failed:", e)

