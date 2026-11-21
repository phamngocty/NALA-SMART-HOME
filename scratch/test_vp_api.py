import urllib.request
import json

try:
    req = urllib.request.urlopen("http://192.168.1.114:8765/api/voiceprint/speakers", timeout=5)
    data = json.loads(req.read().decode('utf-8'))
    print("Voiceprint API Response:\n", json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("API Error:", e)
