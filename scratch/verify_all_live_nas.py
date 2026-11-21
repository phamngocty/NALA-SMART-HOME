import urllib.request
import json
import time

BASE_URL = "http://192.168.1.114:8765"

print("Waiting 3s for container startup...")
time.sleep(3)

# 1. Check index page and all 4 modals
try:
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req, timeout=5) as res:
        html = res.read().decode('utf-8')
        v321 = "v3.2.1" in html
        m1 = "userProfileMemoryModal" in html
        m2 = "livingContextAutomationModal" in html
        m3 = "communicationModal" in html
        m4 = "systemSettingsModal" in html
        print(f"1. Index HTML Check: HTTP {res.status} | v3.2.1: {v321}")
        print(f"   Modals present: UPM={m1}, LCA={m2}, COMM={m3}, SYS={m4}")
except Exception as e:
    print(f"1. Index HTML FAIL: {e}")

# 2. Check TTS Preview
try:
    payload = json.dumps({"text": "Kiểm tra hệ thống Nala", "voice": "vi-VN-HoaiMyNeural", "rate": "+0%", "pitch": "+0Hz"}).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/tts/preview", data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=8) as res:
        audio = res.read()
        print(f"2. TTS Preview: HTTP {res.status} | Received {len(audio)} bytes | Type: {res.headers.get('Content-Type')}")
except Exception as e:
    print(f"2. TTS Preview FAIL: {e}")

# 3. Check All 4 Hub APIs
hub_apis = [
    ("/api/voiceprint/speakers", "Hub 1: Speakers List"),
    ("/api/memory", "Hub 1: Learned Memory"),
    ("/api/living-context", "Hub 2: Living Context FSM"),
    ("/api/automations", "Hub 2: Rule Engine Automations"),
    ("/api/devices", "Hub 3: Intercom Devices"),
    ("/api/history", "Hub 3: History Records"),
    ("/api/ai/config", "Hub 4: AI Config & XiaoZhi Role"),
    ("/api/ha/config", "Hub 4: Home Assistant Config"),
    ("/api/ota/status", "Hub 4: OTA Firmware Status"),
]

print("3. Testing Hub Backend APIs:")
for ep, name in hub_apis:
    try:
        req = urllib.request.Request(f"{BASE_URL}{ep}")
        with urllib.request.urlopen(req, timeout=5) as res:
            data = res.read()
            print(f"   ✅ {name} ({ep}): HTTP {res.status} | {len(data)} bytes")
    except Exception as e:
        print(f"   ❌ {name} ({ep}): FAIL -> {e}")
