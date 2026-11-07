import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)

# Get the first 50 lines of docker logs since container started
stdin, stdout, stderr = ssh.exec_command("docker logs --tail 150 nala_nas_ws_hub 2>&1")
lines = stdout.read().decode('utf-8', errors='replace').splitlines()
print(f"Total lines: {len(lines)}")
for l in lines[:40]:
    print(l)

ssh.close()
