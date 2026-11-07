import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)
    stdin, stdout, stderr = ssh.exec_command("docker logs --tail 40 nala_nas_ws_hub")
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    print("=== DOCKER LOGS (nala_nas_ws_hub) ===")
    print(out)
    if err:
        print("=== STDERR ===")
        print(err)
    ssh.close()
except Exception as e:
    print(f"SSH Error: {e}")
