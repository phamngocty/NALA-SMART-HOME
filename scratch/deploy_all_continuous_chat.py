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

# 1. Upload ai_agent_router.py
local_ai = 'server_nas_hub/app/ai_agent_router.py'
remote_ai = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/ai_agent_router.py'
print(f"1. Uploading {local_ai} -> {remote_ai}")
sftp.put(local_ai, remote_ai)

# 2. Upload main_ws_server.py
local_ws = 'server_nas_hub/app/main_ws_server.py'
remote_ws = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py'
print(f"2. Uploading {local_ws} -> {remote_ws}")
sftp.put(local_ws, remote_ws)

# 3. Upload index.html
local_html = 'server_nas_hub/app/static/index.html'
remote_html = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html'
print(f"3. Uploading {local_html} -> {remote_html}")
sftp.put(local_html, remote_html)

# 4. Upload compiled firmware.bin to OTA directory
local_fw = 'firmware_esp32s3_panel/.pio/build/esp32s3_panel/firmware.bin'
remote_fw = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware/firmware_es3c28p.bin'
print(f"4. Uploading OTA firmware {local_fw} -> {remote_fw}")
sftp.put(local_fw, remote_fw)

sftp.close()

# 5. Restart docker container
print("5. Restarting docker container nala_nas_ws_hub...")
_, out, err = s.exec_command('docker restart nala_nas_ws_hub')
print(out.read().decode('utf-8', errors='ignore'))
err_msg = err.read().decode('utf-8', errors='ignore')
if err_msg:
    print("STDERR:", err_msg)

s.close()
print("DEPLOYMENT COMPLETE 100%!")
