import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)

cmd = """python3 -c "import os, time; os.environ['TZ'] = 'Asia/Ho_Chi_Minh'; time.tzset(); print(time.strftime('%Y-%m-%d %H:%M:%S %Z'))" """
stdin, stdout, stderr = ssh.exec_command(f"docker exec nala_nas_ws_hub {cmd}")
print("Container result with tzset:")
print(stdout.read().decode('utf-8'))
print("Stderr:", stderr.read().decode('utf-8'))

ssh.close()
