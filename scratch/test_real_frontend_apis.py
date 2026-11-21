import urllib.request
import json

BASE = "http://192.168.1.114:8765"

endpoints = [
    # 1. userProfileMemoryModal APIs
    ("GET", "/api/voiceprint/speakers", "Voiceprint Speakers"),
    ("GET", "/api/history?limit=100&type=voice_ai", "Voice History for Enrollment"),
    ("GET", "/api/memory", "Learned Memory Data"),
    
    # 2. livingContextAutomationModal APIs
    ("GET", "/api/living-context", "Living Context Status (FSM & Radar)"),
    ("GET", "/api/automations", "Automation Rules (Rule Engine)"),
    
    # 3. communicationModal APIs
    ("GET", "/api/devices", "Devices (Intercom targets)"),
    ("GET", "/api/intercom/active_calls", "Active Intercom Calls"),
    ("GET", "/api/history", "Communication History"),
    
    # 4. systemSettingsModal APIs
    ("GET", "/api/ai/config", "AI Config (Role, Persona, TTS, LLM)"),
    ("GET", "/api/ha/config", "HA Configuration"),
    ("GET", "/api/ha/areas", "HA Areas / Rooms"),
    ("GET", "/api/ha/entities", "HA Entities"),
    ("GET", "/api/ota/status", "OTA Firmware Status"),
    ("GET", "/api/system/status", "System Status"),
]

print("=== TESTING REAL FRONTEND BACKEND APIS ===")
for method, ep, name in endpoints:
    url = f"{BASE}{ep}"
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as res:
            data = res.read().decode('utf-8')
            print(f"✅ {name} ({ep}): HTTP {res.status} | {len(data)} bytes")
    except Exception as e:
        print(f"❌ {name} ({ep}): FAIL -> {e}")
