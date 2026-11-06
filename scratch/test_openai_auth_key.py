import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

for m in ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]:
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": m, "messages": [{"role": "user", "content": "hi"}]},
        timeout=10
    )
    print(f"Model: {m} -> Status: {r.status_code}")
    print("Response:", r.text[:250])
