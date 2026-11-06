import sys
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8')

url = "http://192.168.1.114:8765/api/ai/chat"
resp = httpx.post(url, json={"message": "Giới thiệu bản thân", "provider": "deepseek"}, timeout=30.0)
print(f"Status Code: {resp.status_code}")
data = resp.json()
print("Reply text:", data.get("reply"))
audio_b64 = data.get("audio_wav_base64", "")
print(f"Audio wav base64 length: {len(audio_b64)} chars (approx {len(audio_b64)*3//4//1024} KB)")
