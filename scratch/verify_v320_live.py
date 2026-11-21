import urllib.request
import urllib.parse
import json
import time

BASE_URL = "http://192.168.1.114:8765"

print("Waiting 3 seconds for container startup...")
time.sleep(3)

# 1. Check index.html version
try:
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req, timeout=5) as res:
        html = res.read().decode('utf-8')
        has_v320 = "v3.2.0" in html
        has_xz = "xzVoiceDropdownContainer" in html
        print(f"1. Index page check: HTTP {res.status} | v3.2.0: {has_v320} | XiaoZhi dropdown: {has_xz}")
except Exception as e:
    print(f"1. Index page check FAIL: {e}")

# 2. Check /api/ai/config
try:
    req = urllib.request.Request(f"{BASE_URL}/api/ai/config")
    with urllib.request.urlopen(req, timeout=5) as res:
        data = json.loads(res.read().decode('utf-8'))
        print(f"2. AI config check: active_provider={data.get('active_provider')}, voice={data.get('tts_voice')}, rate={data.get('tts_rate')}, pitch={data.get('tts_pitch')}, vad={data.get('vad_speed')}")
except Exception as e:
    print(f"2. AI config check FAIL: {e}")

# 3. Test /api/tts/preview endpoint
try:
    preview_payload = json.dumps({
        "text": "Xin chào! Mình là Nala, trợ lý ảo nhà thông minh của bạn.",
        "voice": "vi-VN-HoaiMyNeural",
        "rate": "+0%",
        "pitch": "+0Hz"
    }).encode('utf-8')
    req = urllib.request.Request(f"{BASE_URL}/api/tts/preview", data=preview_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=8) as res:
        audio_bytes = res.read()
        print(f"3. TTS Preview check: HTTP {res.status} | Audio received: {len(audio_bytes)} bytes | Content-Type: {res.headers.get('Content-Type')}")
except Exception as e:
    print(f"3. TTS Preview check FAIL: {e}")
