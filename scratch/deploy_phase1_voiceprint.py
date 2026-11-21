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
    "voiceprint_manager.py",
    "history_manager.py",
    "ai_agent_router.py",
    "main_ws_server.py"
]

print("=== BẮT ĐẦU TẢI LÊN MÁY CHỦ NAS HUB ===")
sftp = ssh.open_sftp()
for f in files_to_upload:
    local_p = f"server_nas_hub/app/{f}"
    remote_p = f"/home/nas152/nala-voice-intercom-system/server_nas_hub/app/{f}"
    print(f"Uploading {f} -> {remote_p}...")
    sftp.put(local_p, remote_p)
sftp.close()

print("\n=== RESTART CONTAINER NALA_NAS_WS_HUB ===")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart output:", stdout.read().decode().strip())

print("\nChờ 4s để container khởi động và nạp model CAM++...")
time.sleep(4)

print("\n=== KIỂM TRA DOCKER LOGS MỚI NHẤT ===")
stdin, stdout, stderr = ssh.exec_command('docker logs --tail 35 nala_nas_ws_hub')
logs = stdout.read().decode('utf-8', errors='replace')
print(logs)

print("\n=== KIỂM TRA REST API VOICEPRINT TỪ NAS ===")
try:
    req = urllib.request.urlopen("http://192.168.1.114:8765/api/voiceprint/speakers", timeout=5)
    data = json.loads(req.read().decode('utf-8'))
    print("Voiceprint API Response:", json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print("API Error:", e)

ssh.close()
