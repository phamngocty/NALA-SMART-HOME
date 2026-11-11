import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    cmd = 'docker logs -t --tail 500 nala_nas_ws_hub 2>&1'
    stdin, stdout, stderr = ssh.exec_command(cmd)
    lines = stdout.read().decode('utf-8', errors='replace').splitlines()
    filtered = []
    ignore_patterns = ["GET /api/devices", "GET /api/system/status", "GET /api/intercom/active_calls", "GET /favicon.ico"]
    for l in lines:
        if not any(p in l for p in ignore_patterns):
            filtered.append(l)
    print("=== LOGS FOR CALL COMMAND ===")
    for l in filtered[-80:]:
        print(l)
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
