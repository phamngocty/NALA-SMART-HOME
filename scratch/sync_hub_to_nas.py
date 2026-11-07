import paramiko
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_USER = 'nas152'
NAS_PASS = '271000'

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect(NAS_IP, username=NAS_USER, password=NAS_PASS)

sftp = s.open_sftp()

# 1. Upload main_ws_server.py
local_ws = 'server_nas_hub/app/main_ws_server.py'
remote_ws = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py'
print(f"Uploading {local_ws} -> {remote_ws}")
sftp.put(local_ws, remote_ws)

# 2. Upload index.html
local_html = 'server_nas_hub/app/static/index.html'
remote_html = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html'
print(f"Uploading {local_html} -> {remote_html}")
sftp.put(local_html, remote_html)

sftp.close()

# 3. Restart Docker container
print("Restarting docker container nala_nas_ws_hub...")
_, out, err = s.exec_command('docker restart nala_nas_ws_hub')
print(out.read().decode('utf-8', errors='ignore'))
err_out = err.read().decode('utf-8', errors='ignore')
if err_out:
    print("ERR:", err_out)

s.close()
print("All synced successfully!")
