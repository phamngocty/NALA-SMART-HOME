import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

sftp = ssh.open_sftp()
for f in ["voiceprint_manager.py", "test_voiceprint_manager.py"]:
    print(f"Uploading {f}...")
    sftp.put(f"server_nas_hub/app/{f}", f"/home/nas152/nala-voice-intercom-system/server_nas_hub/app/{f}")
sftp.close()

print("\nRunning unit test inside container...")
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python3 /app/app/test_voiceprint_manager.py')
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:\n" + out)
if err: print("STDERR:\n" + err)

ssh.close()
