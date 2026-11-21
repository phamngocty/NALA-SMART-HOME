import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

sftp = ssh.open_sftp()
sftp.put('server_nas_hub/app/test_camplus.py', '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/test_camplus.py')
sftp.close()

stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python3 /app/app/test_camplus.py')
print(stdout.read().decode())
err = stderr.read().decode()
if err: print("STDERR:\n", err)

ssh.close()
