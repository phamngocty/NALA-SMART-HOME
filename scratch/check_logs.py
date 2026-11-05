import paramiko, sys
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

stdin, stdout, stderr = ssh.exec_command('docker logs --tail 300 nala_nas_ws_hub')
logs = stdout.read().decode('utf-8') + stderr.read().decode('utf-8')

for line in logs.splitlines():
    if any(k in line for k in ['881C', 'D6F4', 'WebSocket', 'admin', 'ws', 'Error', 'Exception', 'Traceback']):
        print(line)

ssh.close()
