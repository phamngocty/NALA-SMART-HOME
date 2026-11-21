import urllib.request
import json
import base64
import numpy as np

# Create 2 seconds of 16kHz sine wave audio as dummy PCM test
samples = (np.sin(2 * np.pi * 440 * np.linspace(0, 2, 32000)) * 16000).astype(np.int16)
pcm_bytes = samples.tobytes()
b64_audio = base64.b64encode(pcm_bytes).decode('ascii')

# 1. Enroll "TestUser"
url = "http://192.168.1.114:8765/api/voiceprint/enroll"
payload = json.dumps({"name": "TestUser", "audio_base64": b64_audio}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    print("Enroll Response:", json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Enroll Error:", e)

# 2. Check Speakers
resp = urllib.request.urlopen("http://192.168.1.114:8765/api/voiceprint/speakers", timeout=5)
data = json.loads(resp.read().decode())
print("Speakers after enroll:", [s["name"] for s in data["speakers"]])

# 3. Delete "TestUser"
req_del = urllib.request.Request("http://192.168.1.114:8765/api/voiceprint/speakers/TestUser", method='DELETE')
try:
    resp = urllib.request.urlopen(req_del, timeout=5)
    data = json.loads(resp.read().decode())
    print("Delete Response:", json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("Delete Error:", e)

# 4. Final Speakers List
resp = urllib.request.urlopen("http://192.168.1.114:8765/api/voiceprint/speakers", timeout=5)
data = json.loads(resp.read().decode())
print("Final Speakers:", [s["name"] for s in data["speakers"]])
