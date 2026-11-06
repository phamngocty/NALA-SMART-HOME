import os
import sys
import json
import hashlib
import time
import paramiko
import requests
from datetime import datetime

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Firmware details
bin_path = os.path.abspath('firmware_esp32s3_panel/.pio/build/esp32s3_panel/firmware.bin')
if not os.path.exists(bin_path):
    print("Error: firmware.bin not found!")
    sys.exit(1)

file_size = os.path.getsize(bin_path)
size_mb = round(file_size / (1024 * 1024), 2)

hasher = hashlib.md5()
with open(bin_path, 'rb') as f:
    while chunk := f.read(65536):
        hasher.update(chunk)
md5_hash = hasher.hexdigest()
print(f"Firmware binary: {file_size} bytes ({size_mb} MB), MD5: {md5_hash}")

# 2. Connect SFTP
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=8)
sftp = ssh.open_sftp()

# Upload main_ws_server.py
local_server = os.path.abspath('server_nas_hub/app/main_ws_server.py')
remote_server = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py'
print(f"Uploading {local_server} -> {remote_server}...")
sftp.put(local_server, remote_server)

# Upload firmware.bin
remote_firmware_dir = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware'
remote_bin = f"{remote_firmware_dir}/firmware_latest.bin"
remote_meta = f"{remote_firmware_dir}/ota_meta.json"
print(f"Uploading {bin_path} -> {remote_bin}...")
sftp.put(bin_path, remote_bin)

# Update ota_meta.json
meta_data = {
    "latest_file": "firmware_latest.bin",
    "original_filename": "firmware_v3.3.4_rtc_sync.bin",
    "version": "v3.3.4-rtc-sync",
    "size_bytes": file_size,
    "size_mb": size_mb,
    "md5": md5_hash,
    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "download_url": "http://192.168.1.114:8765/api/ota/firmware/firmware_latest.bin",
    "available": True
}

with sftp.file(remote_meta, 'w') as f:
    json.dump(meta_data, f, indent=2)
print("Updated ota_meta.json successfully!")

sftp.close()

# Restart docker container
print("Restarting docker container nala_nas_ws_hub...")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart STDOUT:", stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()

print("Waiting 4s for server to start...")
time.sleep(4)

# Verify /api/ota/status
try:
    ota_res = requests.get("http://192.168.1.114:8765/api/ota/status", timeout=10).json()
    print("OTA Status on NAS:", ota_res.get('version'), ota_res.get('md5'))
except Exception as e:
    print("Error checking OTA status:", e)
