import urllib.request
import json
import base64

# Generate 1.0 second of clean 16kHz 16-bit mono PCM sine wave (440Hz)
import numpy as np

t = np.linspace(0, 1.0, 16000, False)
sine = np.sin(2 * np.pi * 440 * t) * 16384
pcm = sine.astype(np.int16).tobytes()
b64_audio = base64.b64encode(pcm).decode('utf-8')

# Test enroll with name and description
data = json.dumps({
    "name": "Bố",
    "description": "Chủ nhà, quản lý toàn bộ hệ thống",
    "audio_list_base64": [b64_audio]
}).encode('utf-8')

req = urllib.request.Request(
    'http://192.168.1.114:8765/api/voiceprint/enroll',
    data=data,
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=5) as res:
        enroll_res = json.loads(res.read().decode('utf-8'))
        print("Enroll response:", enroll_res)
except Exception as e:
    print("Enroll error:", e)

# Test list speakers
with urllib.request.urlopen('http://192.168.1.114:8765/api/voiceprint/speakers') as res:
    speakers_res = json.loads(res.read().decode('utf-8'))
    print("List speakers response:", speakers_res)
