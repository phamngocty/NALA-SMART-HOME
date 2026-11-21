import requests

base_url = 'http://192.168.1.114:8765'

endpoints = [
    ('/api/voiceprint/speakers', 'GET'),
    ('/api/living-context', 'GET'),
    ('/api/automations', 'GET'),
    ('/api/history?limit=10', 'GET'),
    ('/api/ai/config', 'GET'),
    ('/api/ha/config', 'GET'),
    ('/api/ota/status', 'GET'),
    ('/api/extensions/media_players', 'GET')
]

print("=== VERIFYING REAL NAS HUB ENDPOINTS ===")
all_pass = True
for ep, method in endpoints:
    url = f"{base_url}{ep}"
    try:
        res = requests.get(url, timeout=5)
        print(f"[{res.status_code}] {method} {ep} -> {len(res.content)} bytes")
        if res.status_code != 200:
            all_pass = False
    except Exception as e:
        print(f"[FAIL] {method} {ep} -> {e}")
        all_pass = False

print("\nAll endpoints operational:", all_pass)
