import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

_, out, _ = ssh.exec_command('echo 271000 | sudo -S docker logs --tail 2000 nala_nas_ws_hub | grep -i models')
print(out.read().decode())
ssh.close()
