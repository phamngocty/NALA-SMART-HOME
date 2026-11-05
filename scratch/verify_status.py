import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
with urllib.request.urlopen('http://192.168.1.114:8765/api/devices', timeout=5) as res:
    data = json.loads(res.read().decode('utf-8'))
    for d in data:
        print(f"{d.get('pairing_code')} ({d.get('room_name')}): online={d.get('online')}, fw={d.get('firmware_version')}, ip={d.get('ip')}")
