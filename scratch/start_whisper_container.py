import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = "cd /home/nas152/nala-voice-intercom-system/server_nas_hub && echo 271000 | sudo -S docker compose --profile voice up -d faster_whisper_stt"
print("Running:", cmd)
stdin, stdout, stderr = ssh.exec_command(cmd)
# Let's read the stream
while True:
    line = stdout.readline()
    if not line:
        break
    print(line.strip())

err = stderr.read().decode('utf-8', errors='replace').strip()
if err:
    print("ERR:", err)

ssh.close()
