import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)
stdin, stdout, stderr = ssh.exec_command("docker logs nala_nas_ws_hub | grep -E 'OTA|connect|881C|D6F4' | tail -n 25")
print(stdout.read().decode('utf-8'))
ssh.close()
