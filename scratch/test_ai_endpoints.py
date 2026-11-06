import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

base_url = "http://192.168.1.114:8765"

print("=== 1. Getting current AI Config ===")
res = requests.get(f"{base_url}/api/ai/config")
print("Status:", res.status_code)
cfg = res.json()
print("Safe Config:", json.dumps(cfg, indent=2, ensure_ascii=False))

print("\n=== 2. Testing Gemini Endpoint ===")
test_payload_gemini = {
    "provider": "gemini",
    "model": "gemini-3.8-flash"
}
try:
    res = requests.post(f"{base_url}/api/ai/test", json=test_payload_gemini, timeout=20)
    print("Gemini Test Status:", res.status_code)
    print("Gemini Test Response:", res.json())
except Exception as e:
    print("Gemini Test Exception:", e)

print("\n=== 3. Testing DeepSeek Endpoint ===")
test_payload_deepseek = {
    "provider": "deepseek",
    "model": "deepseek-flash"
}
try:
    res = requests.post(f"{base_url}/api/ai/test", json=test_payload_deepseek, timeout=20)
    print("DeepSeek Test Status:", res.status_code)
    print("DeepSeek Test Response:", res.json())
except Exception as e:
    print("DeepSeek Test Exception:", e)
