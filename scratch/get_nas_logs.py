import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')
_, out, err = ssh.exec_command('echo 271000 | sudo -S docker logs --tail 50 nala_nas_ws_hub')
print(out.read().decode('utf-8', errors='replace'))
ssh.close()
