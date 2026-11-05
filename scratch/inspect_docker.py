import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)

stdin, stdout, stderr = ssh.exec_command("docker inspect nala_nas_ws_hub")
raw = stdout.read().decode('utf-8')
import json
data = json.loads(raw)[0]
mounts = data.get('Mounts', [])
for m in mounts:
    print(m.get('Source'), "->", m.get('Destination'))
ssh.close()
