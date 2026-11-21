import urllib.request
import json

resp = urllib.request.urlopen("http://192.168.1.114:8765/api/ai/config", timeout=5)
data = json.loads(resp.read().decode())
print("Active Provider:", data.get("active_provider"))
for p in ["gemini", "groq", "deepseek", "openrouter"]:
    cfg = data.get(p, {})
    k = cfg.get("api_key", "")
    print(f"Provider {p}: model={cfg.get('model')}, has_key={bool(k)}, masked_key={k[:6] if k else 'EMPTY'}")
