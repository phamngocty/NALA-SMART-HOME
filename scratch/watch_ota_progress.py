import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    for _ in range(6):
        stdin, stdout, stderr = ssh.exec_command('docker logs -t --tail 25 nala_nas_ws_hub 2>&1')
        lines = stdout.read().decode('utf-8', errors='replace').splitlines()
        for l in lines:
            if any(k in l for k in ["OTA", "ota", "881C", "D6F4", "v3.6"]):
                print(l)
        print("---")
        time.sleep(3)
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
