import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    stdin, stdout, stderr = ssh.exec_command('grep -n "admin_sockets" /home/nas152/nala-voice-intercom-system/server_nas_hub/app/intercom_router.py')
    print(stdout.read().decode('utf-8', errors='replace'))
    ssh.close()
except Exception as e:
    print(f"Error: {e}")
