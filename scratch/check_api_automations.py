import requests
import json

res = requests.get('http://192.168.1.114:8765/api/automations')
print("Status:", res.status_code)
print(json.dumps(res.json(), indent=2, ensure_ascii=False))
