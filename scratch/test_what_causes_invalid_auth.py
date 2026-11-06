import httpx

url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

keys_to_test = [
    "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw ", # trailing space
    "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw\n", # newline
    "AQ.Ab8RN6Knoug0OVEzQ", # partial
    "sk-55220366d5ff46e5be8ebe545428f3ef", # deepseek key in gemini
    "AIzaSyDummyKey1234567890", # fake old key
    "AQ.fakeauthkey1234567890" # fake auth key
]

for k in keys_to_test:
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
        json={"model": "gemini-3.8-flash", "messages": [{"role": "user", "content": "hi"}]},
        timeout=10
    )
    print(f"Key: {k[:15]}... -> Status: {r.status_code} -> Body: {r.text.strip()}")
