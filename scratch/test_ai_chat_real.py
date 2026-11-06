import sys
import requests
import json
import base64

sys.stdout.reconfigure(encoding='utf-8')

url = "http://192.168.1.114:8765/api/ai/chat"
payload = {
    "message": "Chào bạn, bạn là ai?",
    "provider": "deepseek"
}

print(f"Sending test chat to {url}...")
res = requests.post(url, json=payload, timeout=20)
print("Status code:", res.status_code)
data = res.json()
print("Reply text:", data.get("reply"))
print("Voice:", data.get("voice"))
b64 = data.get("audio_wav_base64", "")
if b64:
    audio_bytes = base64.b64decode(b64)
    print(f"SUCCESS! Audio WAV received: {len(audio_bytes)} bytes!")
else:
    print("FAILED: No audio_wav_base64 in response!")
