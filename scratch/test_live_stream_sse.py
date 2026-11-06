import sys
import time
import json
import httpx

sys.stdout.reconfigure(encoding='utf-8')

url = "http://192.168.1.114:8765/api/ai/chat/stream"
payload = {"message": "Chào Nala, bạn có thể làm được những gì?", "provider": "deepseek"}

print(f"Testing SSE Stream to {url}...")
start_t = time.time()
first_token_t = None
token_count = 0
audio_received = False
full_text = ""

try:
    with httpx.stream("POST", url, json=payload, timeout=30.0) as resp:
        print(f"Status Code: {resp.status_code}")
        if resp.status_code != 200:
            print("Error response:", resp.read().decode('utf-8'))
            sys.exit(1)

        event_name = ""
        for line in resp.iter_lines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("event: "):
                event_name = line[7:]
            elif line.startswith("data: "):
                data_str = line[6:]
                data = json.loads(data_str)
                if event_name == "token":
                    if first_token_t is None:
                        first_token_t = time.time()
                        print(f"TTFT (Time To First Token): {(first_token_t - start_t)*1000:.0f}ms")
                    chunk = data.get("chunk", "")
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
                    token_count += 1
                elif event_name == "audio":
                    wav_b64 = data.get("audio_wav_base64", "")
                    if wav_b64:
                        audio_received = True
                        print(f"\n[Audio Received: {len(wav_b64)} chars base64, ~{len(wav_b64)*3//4//1024} KB]")
                elif event_name == "done":
                    full_text = data.get("full_text", "")
                    print(f"\n[Stream Completed in {(time.time() - start_t):.2f}s]")

    print("\nSummary:")
    print("Token count:", token_count)
    print("Audio received:", audio_received)
    print("Full text length:", len(full_text))

except Exception as e:
    print(f"Error during SSE test: {e}")
