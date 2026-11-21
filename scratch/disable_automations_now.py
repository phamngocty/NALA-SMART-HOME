import urllib.request
import json

url = "http://192.168.1.114:8765/api/automations"
resp = urllib.request.urlopen(url, timeout=5)
data = json.loads(resp.read().decode())

for r in data["rules"]:
    rule_id = r["id"]
    toggle_url = f"{url}/{rule_id}/toggle"
    req = urllib.request.Request(
        toggle_url,
        data=json.dumps({"enabled": False}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    res = urllib.request.urlopen(req, timeout=5)
    print(f"Disabled {rule_id}:", res.read().decode())

print("\nVerifying automations disabled:")
resp = urllib.request.urlopen(url, timeout=5)
data = json.loads(resp.read().decode())
for r in data["rules"]:
    print(f"- {r['id']}: enabled = {r.get('enabled')}")
