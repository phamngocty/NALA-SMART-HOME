import requests
import json
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

NAS_URL = "http://192.168.1.114:8765"

print("--- 1. Testing Normal AI Chat Endpoint ---")
payload = {
    "message": "Bật đèn phòng khách",
}
t0 = time.time()
try:
    r = requests.post(f"{NAS_URL}/api/ai/chat", json=payload, timeout=12)
    elapsed = time.time() - t0
    print(f"Status Code: {r.status_code} in {elapsed:.2f}s")
    if r.status_code == 200:
        data = r.json()
        print(f"Reply: '{data.get('reply')}'")
        print(f"Audio wav bytes: {len(data.get('audio_wav_base64', ''))}")
    else:
        print(f"Error: {r.text}")
except Exception as e:
    print(f"Request failed: {e}")

print("\n--- 2. Testing Streaming AI Chat Endpoint ---")
t0 = time.time()
try:
    with requests.post(f"{NAS_URL}/api/ai/chat/stream", json=payload, stream=True, timeout=12) as r:
        print(f"Stream status: {r.status_code}")
        first_chunk = True
        chunks = []
        for line in r.iter_lines():
            line_str = line.decode('utf-8', errors='replace')
            if line_str.startswith("data: "):
                data_part = line_str[6:].strip()
                try:
                    c = json.loads(data_part)
                    chunk = c.get("chunk", "")
                    if chunk:
                        if first_chunk:
                            print(f"Time to first token (TTFT): {time.time() - t0:.2f}s")
                            first_chunk = False
                        chunks.append(chunk)
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    if "full_text" in c:
                        print(f"\n[DONE event] full_text: '{c.get('full_text')}'")
                except Exception:
                    pass
        print(f"\nTotal stream time: {time.time() - t0:.2f}s")
except Exception as e:
    print(f"Stream request failed: {e}")
