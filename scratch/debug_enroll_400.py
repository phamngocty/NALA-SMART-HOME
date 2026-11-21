import urllib.request
import json
import base64
import numpy as np

# Generate 2.0s of audio (speech-like sine mixture)
t = np.linspace(0, 2.0, 32000, False)
sine = (np.sin(2 * np.pi * 200 * t) + np.sin(2 * np.pi * 400 * t)) * 8000
pcm = sine.astype(np.int16).tobytes()
b64_audio = base64.b64encode(pcm).decode('utf-8')

data = json.dumps({
    "name": "Bố",
    "description": "Chủ nhà",
    "audio_list_base64": [b64_audio]
}).encode('utf-8')

req = urllib.request.Request(
    'http://192.168.1.114:8765/api/voiceprint/enroll',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=5) as res:
        print("Success:", res.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read().decode('utf-8'))
