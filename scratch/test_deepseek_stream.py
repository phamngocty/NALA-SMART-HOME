import asyncio
import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

api_key = "sk-46d4e2444af24df5b853c8fb16d60e08"
url = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "deepseek-flash",
    "messages": [
        {"role": "system", "content": "Bạn là trợ lý Nala. Trả lời ngắn gọn 1 câu."},
        {"role": "user", "content": "Giới thiệu bản thân"}
    ],
    "stream": True,
    "thinking": {"type": "disabled"},
    "max_tokens": 100
}

async def test_stream():
    print("Connecting to DeepSeek stream...")
    async with httpx.AsyncClient(timeout=20.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            print("Status code:", response.status_code)
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:]
                    if data_str == "[DONE]":
                        print("\n[STREAM DONE]")
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        chunk = delta.get("content", "")
                        if chunk:
                            sys.stdout.write(chunk)
                            sys.stdout.flush()
                    except Exception as e:
                        print("\nErr parsing:", e)

asyncio.run(test_stream())
