import urllib.request
import json

BASE_URL = "http://192.168.1.114:8765"

voices_to_test = [
    ("vi-VN-HoaiMyNeural", "+0%", "+0Hz", "Giọng nữ (Female Voice) - Hoài My"),
    ("vi-VN-NamMinhNeural", "+0%", "+0Hz", "giọng nam (Male Voice) - Nam Minh"),
    ("vi-VN-HoaiMyNeural", "+10%", "+10Hz", "cô gái trẻ (Young Girl)"),
    ("vi-VN-NamMinhNeural", "-5%", "-10Hz", "chủ nhà nam (Male Host)"),
    ("vi-VN-NamMinhNeural", "+10%", "+5Hz", "chàng trai trẻ (Young Man)"),
    ("google_fast", "+0%", "+0Hz", "Thử nghiệm · Google Siêu Tốc (0.15s)"),
]

for voice, rate, pitch, name in voices_to_test:
    payload = json.dumps({
        "text": f"Xin chào! Mình là {name}.",
        "voice": voice,
        "rate": rate,
        "pitch": pitch
    }).encode('utf-8')
    try:
        req = urllib.request.Request(f"{BASE_URL}/api/tts/preview", data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=8) as res:
            audio = res.read()
            print(f"✅ {name}: HTTP {res.status} | {len(audio)} bytes | Type: {res.headers.get('Content-Type')}")
    except Exception as e:
        print(f"❌ {name}: FAIL -> {e}")
