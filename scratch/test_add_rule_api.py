import requests
import json

test_rule = {
    "name": "Test Rule From Python",
    "description": "Test rule description",
    "enabled": True,
    "trigger": {
        "type": "living_context",
        "state": "active"
    },
    "conditions": {
        "target_room": "Phòng Khách"
    },
    "actions": [
        {
            "domain": "light",
            "service": "turn_on",
            "data": { "brightness_pct": 50 }
        }
    ]
}

res = requests.post('http://192.168.1.114:8765/api/automations', json=test_rule)
print("POST status:", res.status_code)
print(res.json())

# Delete it right away
if res.status_code == 200:
    rule_data = res.json().get('rule', {})
    rid = rule_data.get('id')
    print("Deleting test rule:", rid)
    del_res = requests.delete(f'http://192.168.1.114:8765/api/automations/{rid}')
    print("Delete status:", del_res.status_code, del_res.json())
