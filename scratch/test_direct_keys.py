import httpx

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
r = httpx.get(url, timeout=10)
print("Gemini Status:", r.status_code)
print("Gemini Body:", r.text)

# Also test DeepSeek key
ds_key = "sk-55220366d5ff46e5be8ebe545428f3ef"
r2 = httpx.get("https://api.deepseek.com/models", headers={"Authorization": f"Bearer {ds_key}"}, timeout=10)
print("DeepSeek Status:", r2.status_code)
print("DeepSeek Body:", r2.text)
