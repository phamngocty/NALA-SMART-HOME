import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('echo 271000 | sudo -S docker logs --tail 40 nala_nas_ws_hub 2>&1')
full_logs = stdout.read().decode('utf-8', errors='replace')
ssh.close()

for line in full_logs.splitlines():
    print(line.encode('ascii', errors='replace').decode('ascii'))
