import httpx
import time

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={key}"

t0 = time.time()
print("Sending request to gemini-3.8-flash...")
try:
    r = httpx.post(url, json={"contents": [{"parts": [{"text": "Hi, reply 1 word: OK"}]}]}, timeout=30.0)
    print("Elapsed:", round(time.time() - t0, 2), "s")
    print("Status code:", r.status_code)
    print("Response text:", r.text)
except Exception as e:
    print("Error:", e)
