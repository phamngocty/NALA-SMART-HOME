import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)
stdin, stdout, stderr = ssh.exec_command('find /home/nas152/ -name "*.wav" 2>/dev/null | head -n 20')
print("WAV files on NAS:\n", stdout.read().decode())
ssh.close()
