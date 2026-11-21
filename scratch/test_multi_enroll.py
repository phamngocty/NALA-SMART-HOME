import urllib.request
import json
import base64
import numpy as np

# Generate 3 different samples (simulating 3 utterances from Mom)
samples_b64 = []
for freq in [300, 350, 400]:
    t = np.linspace(0, 1.5, 24000, False)
    sine = (np.sin(2 * np.pi * freq * t) * 16384).astype(np.int16).tobytes()
    samples_b64.append(base64.b64encode(sine).decode('utf-8'))

data = json.dumps({
    "name": "Mẹ",
    "description": "Nội trợ, yêu thích nhạc Baroque",
    "audio_list_base64": samples_b64
}).encode('utf-8')

req = urllib.request.Request(
    'http://192.168.1.114:8765/api/voiceprint/enroll',
    data=data,
    headers={'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=5) as res:
    print("Multi-sample Enroll response:", json.loads(res.read().decode('utf-8')))

# Check list speakers
with urllib.request.urlopen('http://192.168.1.114:8765/api/voiceprint/speakers') as res:
    speakers_res = json.loads(res.read().decode('utf-8'))
    print("Updated speakers:", speakers_res)
