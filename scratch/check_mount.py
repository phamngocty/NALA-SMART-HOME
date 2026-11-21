import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)
stdin, stdout, stderr = ssh.exec_command('docker inspect nala_nas_ws_hub --format "{{json .Mounts}}"')
print("Mounts:\n", stdout.read().decode())
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub pwd')
print("Container default dir:\n", stdout.read().decode())
ssh.close()
