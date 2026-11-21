import urllib.request
import json

BASE = "http://192.168.1.114:8765"

endpoints = [
    # 1. userProfileMemoryModal APIs
    ("GET", "/api/voiceprint/speakers", "Voiceprint Speakers"),
    ("GET", "/api/voice/history", "Voice History for Enrollment"),
    ("GET", "/api/history/calls", "Call History"),
    ("GET", "/api/memory/data", "Learned Memory Data"),
    
    # 2. livingContextAutomationModal APIs
    ("GET", "/api/context/status", "Living Context Status (FSM & Radar)"),
    ("GET", "/api/automation/rules", "Automation Rules (Rule Engine)"),
    
    # 3. communicationModal APIs
    ("GET", "/api/devices/paired", "Intercom Devices"),
    ("GET", "/api/history/calls", "Communication Call History"),
    
    # 4. systemSettingsModal APIs
    ("GET", "/api/ai/config", "AI Config (Role, Persona, TTS, LLM)"),
    ("GET", "/api/ha/status", "HA Connection Status"),
    ("GET", "/api/ota/files", "OTA Firmware Files"),
]

print("=== TESTING ALL MODAL BACKEND APIS ===")
for method, ep, name in endpoints:
    url = f"{BASE}{ep}"
    try:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as res:
            data = res.read().decode('utf-8')
            print(f"✅ {name} ({ep}): HTTP {res.status} | {len(data)} bytes")
    except Exception as e:
        print(f"❌ {name} ({ep}): FAIL -> {e}")
