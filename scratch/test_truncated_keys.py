import httpx

url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

keys_to_test = [
    "AQ.Ab8RN6Knoug0OVEzQ", # truncated auth key
    "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw", # exact auth key
    "sk-55220366d5ff46e5be8ebe545428f3ef", # deepseek key in gemini
    "AQ.12345678", # short auth key
    "AIzaSyDummy123456" # fake standard key
]

for k in keys_to_test:
    try:
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": "gemini-3.8-flash", "messages": [{"role": "user", "content": "hi"}]},
            timeout=10
        )
        print(f"Key: {k[:15]}... -> Status: {r.status_code} -> Body: {r.text.strip()}")
    except Exception as e:
        print(f"Key: {k[:15]}... -> Error: {e}")
