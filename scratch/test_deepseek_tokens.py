import sys
import httpx

sys.stdout.reconfigure(encoding='utf-8')

new_key = "sk-46d4e2444af24df5b853c8fb16d60e08"

for mt in [10, 50, 150]:
    r = httpx.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {new_key}", "Content-Type": "application/json"},
        json={"model": "deepseek-flash", "messages": [{"role": "user", "content": "Trả lời OK"}], "max_tokens": mt},
        timeout=10
    )
    data = r.json()
    msg = data['choices'][0]['message']
    print(f"max_tokens={mt} -> content: '{msg.get('content')}', reasoning: '{msg.get('reasoning_content')}'")
