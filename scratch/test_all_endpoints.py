import urllib.request
import json

endpoints = [
    ('/', 'HTML'),
    ('/api/devices', 'Devices'),
    ('/api/ai/config', 'AI Config'),
    ('/api/history?limit=10', 'History'),
    ('/api/voiceprint/speakers', 'Voiceprint Speakers'),
    ('/api/automations', 'Automations'),
    ('/api/living-context', 'Living Context'),
    ('/api/memory', 'Memory'),
    ('/api/ota/status', 'OTA Status'),
    ('/api/wake/config', 'Wake Config'),
]

for ep, desc in endpoints:
    url = f"http://192.168.1.114:8765{ep}"
    try:
        resp = urllib.request.urlopen(url, timeout=5)
        print(f"✅ {desc:22} {ep:25} -> {resp.status} OK")
    except Exception as e:
        print(f"❌ {desc:22} {ep:25} -> ERROR: {e}")
