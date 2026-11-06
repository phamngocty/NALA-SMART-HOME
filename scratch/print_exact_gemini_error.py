import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
r = httpx.post(url, json={"contents": [{"parts": [{"text": "hi"}]}]}, timeout=15)
print("Full error text:")
print(r.text)
