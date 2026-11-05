import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)
stdin, stdout, stderr = ssh.exec_command("sudo docker logs nala_nas_ws_hub --tail 100", get_pty=True)
stdin.write('271000\n')
stdin.flush()
lines = stdout.read().decode('utf-8', errors='replace').splitlines()
for line in lines:
    if "121" in line or "D6F4" in line or "118" in line or "881C" in line:
        print(line)
ssh.close()
