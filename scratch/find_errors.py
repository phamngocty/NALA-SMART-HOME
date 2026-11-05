import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)
stdin, stdout, stderr = ssh.exec_command("sudo docker logs nala_nas_ws_hub --tail 150", get_pty=True)
stdin.write('271000\n')
stdin.flush()
lines = stdout.read().decode('utf-8', errors='replace').splitlines()
for line in lines:
    if "Exception" in line or "Error" in line or "Traceback" in line or "disconnected" in line:
        print(line)
ssh.close()
