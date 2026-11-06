import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"

for model in ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-1.5-flash"]:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [
            {"parts": [{"text": "Chào bạn, hãy trả lời ngắn gọn 1 từ: OK"}]}
        ]
    }
    r = httpx.post(url, json=payload, timeout=10)
    print(f"Model: {model} -> Status: {r.status_code}")
    if r.status_code == 200:
        print("Reply:", r.json()['candidates'][0]['content']['parts'][0]['text'])
    else:
        print("Error:", r.text[:200])
