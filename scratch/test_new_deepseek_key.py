import httpx

new_key = "sk-46d4e2444af24df5b853c8fb16d60e08"

r = httpx.post(
    "https://api.deepseek.com/chat/completions",
    headers={"Authorization": f"Bearer {new_key}", "Content-Type": "application/json"},
    json={"model": "deepseek-flash", "messages": [{"role": "user", "content": "hi"}]},
    timeout=10
)
print("DeepSeek Status:", r.status_code)
print("DeepSeek Response:", r.text)
