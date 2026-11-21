import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('ps aux | grep 4110325; echo ---; ps aux | grep 4110337; echo ---; ps aux | grep python')
print(stdout.read().decode())
ssh.close()
