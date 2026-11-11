import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    # Filter out HTTP polling
    stdin, stdout, stderr = ssh.exec_command('docker logs -t --tail 3000 nala_nas_ws_hub 2>&1')
    lines = stdout.read().decode('utf-8', errors='replace').splitlines()
    filtered = []
    ignore_patterns = ["GET /api/devices", "GET /api/system/status", "GET /api/intercom/active_calls", "GET /favicon.ico"]
    for l in lines:
        if not any(p in l for p in ignore_patterns):
            filtered.append(l)
    print(f"Total lines: {len(lines)}, Filtered interesting lines: {len(filtered)}")
    print("=== LAST 60 FILTERED LINES ===")
    for l in filtered[-60:]:
        print(l)
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
