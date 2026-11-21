import urllib.request
import json

# Check the active automations
resp = urllib.request.urlopen("http://192.168.1.114:8765/api/automations", timeout=5)
data = json.loads(resp.read().decode())
print("Total Active Automations:", len(data["rules"]))
for r in data["rules"]:
    print(f"- [{r.get('id')}]: {r.get('name')} (trigger: {r.get('trigger', {}).get('state')})")
