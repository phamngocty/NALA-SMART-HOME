import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python /app/app/benchmark_chunk_tts.py')
print("Output:\n", stdout.read().decode('utf-8'))
print("Error:\n", stderr.read().decode('utf-8'))

ssh.close()
