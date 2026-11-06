import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')
with urllib.request.urlopen('http://192.168.1.114:8765/api/devices', timeout=3) as resp:
    data = json.loads(resp.read().decode())
    for d in data:
        print(f"Device: {d.get('device_code')} | IP: {d.get('ip')} | Online: {d.get('online')} | Room: {d.get('room_name')}")
