import paramiko
import difflib

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

sftp = ssh.open_sftp()
with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py', 'r') as f:
    nas_text = f.read().decode('utf-8')
sftp.close()
ssh.close()

with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    local_text = f.read()

diff = list(difflib.unified_diff(
    nas_text.splitlines(keepends=True),
    local_text.splitlines(keepends=True),
    fromfile='NAS',
    tofile='LOCAL',
    n=3
))
print(''.join(diff[:100]))
