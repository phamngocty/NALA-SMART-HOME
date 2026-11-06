import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
models_to_test = [
    "gemini-3.8-flash",
    "gemini-3.0-flash",
    "gemini-2.0-flash-exp",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b",
    "gemini-flash-latest"
]

for m in models_to_test:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    try:
        r = httpx.post(url, json={"contents": [{"parts": [{"text": "Xin chào NALA"}]}]}, timeout=15)
        print(f"Model: {m} -> Code: {r.status_code}")
        if r.status_code == 200:
            candidate = r.json().get('candidates', [{}])[0]
            text = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"  >>> SUCCESS! Response: {text[:80]}")
        else:
            print(f"  >>> Failed: {r.text[:120]}")
    except Exception as e:
        print(f"Model: {m} -> Error: {e}")
