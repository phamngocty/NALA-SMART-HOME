import sys
import httpx
import json

sys.stdout.reconfigure(encoding='utf-8')

url = "http://192.168.1.114:8765/api/ai/tts"
sample_text = 'Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh, kích hoạt kịch bản như "xem phim" hay "đi ngủ", và tắt hết thiết bị khi bạn ra khỏi nhà. Cứ ra lệnh tự nhiên nhé!'

resp = httpx.post(url, json={"text": sample_text, "voice": "vi-VN-NamMinhNeural"}, timeout=30.0)
print(f"Status Code: {resp.status_code}")
data = resp.json()
print("Status in json:", data.get("status"))
audio_b64 = data.get("audio_wav_base64", "")
print(f"Audio length base64: {len(audio_b64)}")
