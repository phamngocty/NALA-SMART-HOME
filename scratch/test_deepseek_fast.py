import sys
import httpx
import time

sys.stdout.reconfigure(encoding='utf-8')
new_key = "sk-46d4e2444af24df5b853c8fb16d60e08"

t0 = time.time()
r = httpx.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": f"Bearer {new_key}", "Content-Type": "application/json"},
    json={
        "model": "deepseek-flash",
        "messages": [{"role": "user", "content": "Trả lời OK"}],
        "thinking": {"type": "disabled"},
        "max_tokens": 50
    },
    timeout=10
)
print("Time:", round(time.time() - t0, 2), "s")
data = r.json()
print("Response:", data['choices'][0]['message'])
