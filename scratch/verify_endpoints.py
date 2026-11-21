import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

endpoints = [
    '/api/devices',
    '/api/voiceprint/speakers',
    '/api/living-context',
    '/api/automations',
    '/api/history?limit=5',
    '/api/history/settings',
    '/api/memory/all',
]

for ep in endpoints:
    try:
        res = urllib.request.urlopen(f'http://192.168.1.114:8765{ep}', timeout=5)
        body = json.loads(res.read().decode('utf-8'))
        print(f"{ep}: 200 OK - status: {body.get('status')}")
    except Exception as e:
        print(f"{ep} ERROR: {e}")
