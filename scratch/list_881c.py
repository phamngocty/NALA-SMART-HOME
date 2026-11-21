import urllib.request
import json

url = 'http://192.168.1.27:8123/api/states'
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ODVkMDk4OWQ4ZmU0ZGUzYjVjMmViMjUzZTc0ZGYxNyIsImlhdCI6MTc5MzE4NjYzMiwiZXhwIjoyMTA4NTQ2NjMyfQ.y_GNcmplg0t63Z-r3J232Lvhy1a1LfFzyQyJGFDQzWA'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req) as resp:
    states = json.loads(resp.read().decode())
    for s in states:
        if '881c' in s['entity_id'] or 'phong_ty' in s['entity_id'] or 'phong_ngu_ty' in s['entity_id']:
            name = s.get('attributes', {}).get('friendly_name', '')
            print(f"{s['entity_id']} = {s['state']} [{name}]")
