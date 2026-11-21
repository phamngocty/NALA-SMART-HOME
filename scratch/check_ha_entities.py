import urllib.request
import json

url = 'http://192.168.1.27:8123/api/states'
token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ODVkMDk4OWQ4ZmU0ZGUzYjVjMmViMjUzZTc0ZGYxNyIsImlhdCI6MTc5MzE4NjYzMiwiZXhwIjoyMTA4NTQ2NjMyfQ.y_GNcmplg0t63Z-r3J232Lvhy1a1LfFzyQyJGFDQzWA'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        states = json.loads(resp.read().decode())
        nala_states = [s for s in states if 'nala_panel' in s['entity_id']]
        print(f"Total NALA entities: {len(nala_states)}")
        for s in nala_states:
            name = s.get('attributes', {}).get('friendly_name', '')
            print(f"- {s['entity_id']}: {s['state']} [{name}]")
except Exception as e:
    print('Error:', e)
