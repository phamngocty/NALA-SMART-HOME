import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('cd /home/nas152/nala-voice-intercom-system/server_nas_hub && docker compose up -d')
print("COMPOSE UP:", stdout.read().decode())
print("ERR:", stderr.read().decode())

ssh.close()
