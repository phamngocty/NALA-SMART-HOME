import requests

res = requests.post('http://192.168.1.114:8765/api/automations/rule_night_sleep_guard/toggle')
print("Toggle Status:", res.status_code)
print(res.json())
