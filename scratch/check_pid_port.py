import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('echo 271000 | sudo -S ss -tlpn | grep 3960387')
print(stdout.read().decode())
ssh.close()
