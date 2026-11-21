import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'find /home/nas152/nala-voice-intercom-system/ -name ".env*"; find /home/nas152/nala-voice-intercom-system/ -name "*config*.json"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())

cmd2 = 'cat /home/nas152/nala-voice-intercom-system/server_nas_hub/.env 2>/dev/null || cat /home/nas152/nala-voice-intercom-system/.env 2>/dev/null'
stdin, stdout, stderr = ssh.exec_command(cmd2)
env_out = stdout.read().decode()
# Mask sensitive strings
for line in env_out.splitlines():
    if "KEY" in line or "SECRET" in line or "TOKEN" in line:
        k, _, v = line.partition("=")
        print(f"{k}={v[:6]}...{v[-4:] if len(v)>10 else ''}")
    else:
        print(line)

ssh.close()
