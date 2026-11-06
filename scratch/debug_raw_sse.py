import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')

url = "http://192.168.1.114:8765/api/ai/chat/stream"
payload = {"message": "Bật đèn phòng khách", "provider": "deepseek"}

with httpx.stream("POST", url, json=payload, timeout=30.0) as resp:
    for line in resp.iter_lines():
        if line:
            if "audio_wav_base64" in line:
                print(f"LINE: data: {line[:50]}... [len {len(line)}]")
            else:
                print(f"LINE: {line}")
