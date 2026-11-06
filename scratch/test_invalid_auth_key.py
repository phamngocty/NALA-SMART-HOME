import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"

# Test 1: x-goog-api-key header on generateContent
url1 = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent"
headers1 = {"x-goog-api-key": key, "Content-Type": "application/json"}
body1 = {"contents": [{"parts": [{"text": "Hi"}]}]}
r1 = httpx.post(url1, headers=headers1, json=body1, timeout=10)
print("Test 1 (x-goog-api-key):", r1.status_code, r1.text)

# Test 2: Authorization: Bearer on generateContent
headers2 = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
r2 = httpx.post(url1, headers=headers2, json=body1, timeout=10)
print("Test 2 (Bearer):", r2.status_code, r2.text)

# Test 3: ?key= query parameter on generateContent
url3 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={key}"
r3 = httpx.post(url3, json=body1, timeout=10)
print("Test 3 (?key=):", r3.status_code, r3.text)

# Test 4: OpenAI endpoint with Bearer key
url4 = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
headers4 = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
body4 = {"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": "hi"}]}
r4 = httpx.post(url4, headers=headers4, json=body4, timeout=10)
print("Test 4 (OpenAI Bearer):", r4.status_code, r4.text)
