import paramiko
import time
import sys
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

files_to_upload = [
    ("server_nas_hub/app/ai_agent_router.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/ai_agent_router.py"),
    ("server_nas_hub/app/main_ws_server.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py"),
    ("server_nas_hub/app/static/index.html", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html"),
]

print("=== BẮT ĐẦU TẢI LÊN MÁY CHỦ NAS HUB ===")
sftp = ssh.open_sftp()
for loc, rem in files_to_upload:
    print(f"Uploading {loc} -> {rem}...")
    sftp.put(loc, rem)
sftp.close()

print("\n=== RESTART CONTAINER NALA_NAS_WS_HUB ===")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart output:", stdout.read().decode().strip())

print("\nChờ 5s để container khởi động...")
time.sleep(5)

print("\n=== KIỂM TRA DOCKER LOGS MỚI NHẤT ===")
stdin, stdout, stderr = ssh.exec_command('docker logs --tail 30 nala_nas_ws_hub')
logs = stdout.read().decode('utf-8', errors='replace')
print(logs)

ssh.close()

print("\n=== KIỂM TRA TOÀN DIỆN CÁC API TRÊN NAS ===")
# 1. Models scan
for prov in ['gemini', 'groq', 'deepseek', 'openrouter']:
    try:
        data = json.dumps({'provider': prov, 'api_key': ''}).encode('utf-8')
        req = urllib.request.Request('http://192.168.1.114:8765/api/ai/models', data=data, headers={'Content-Type': 'application/json'})
        res = urllib.request.urlopen(req, timeout=8)
        body = json.loads(res.read().decode('utf-8'))
        print(f"[API] /api/ai/models ({prov}): {body.get('status')} - {len(body.get('models', []))} models")
    except Exception as e:
        print(f"[API ERROR] /api/ai/models ({prov}): {e}")

# 2. Voiceprint speakers
try:
    res = urllib.request.urlopen('http://192.168.1.114:8765/api/voiceprint/speakers', timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    print(f"[API] /api/voiceprint/speakers: {body.get('status')} - count: {len(body.get('speakers', []))}")
except Exception as e:
    print(f"[API ERROR] /api/voiceprint/speakers: {e}")

# 3. Automations
try:
    res = urllib.request.urlopen('http://192.168.1.114:8765/api/automations', timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    rules = body.get('rules', [])
    print(f"[API] /api/automations: {len(rules)} rules - Active: {[r['rule_id'] for r in rules if r.get('enabled')]}")
except Exception as e:
    print(f"[API ERROR] /api/automations: {e}")

# 4. Living Context
try:
    res = urllib.request.urlopen('http://192.168.1.114:8765/api/living-context', timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    print(f"[API] /api/living-context: status={body.get('status')}, rooms={list(body.get('rooms', {}).keys())}")
except Exception as e:
    print(f"[API ERROR] /api/living-context: {e}")

print("\n=== HOÀN TẤT ĐỒNG BỘ & KIỂM TRA ===")
