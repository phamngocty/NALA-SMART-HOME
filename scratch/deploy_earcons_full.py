import os
import sys
import json
import hashlib
import time
import paramiko
import requests
from datetime import datetime

# 1. Firmware details
bin_path = os.path.abspath('firmware_esp32s3_panel/.pio/build/esp32s3_panel/firmware.bin')
file_size = os.path.getsize(bin_path)
size_mb = round(file_size / (1024 * 1024), 2)

hasher = hashlib.md5()
with open(bin_path, 'rb') as f:
    while chunk := f.read(65536):
        hasher.update(chunk)
md5_hash = hasher.hexdigest()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=8)
sftp = ssh.open_sftp()

# Upload index.html
sftp.put(
    os.path.abspath('server_nas_hub/app/static/index.html'),
    '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html'
)

# Upload firmware.bin
remote_firmware_dir = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware'
sftp.put(bin_path, f"{remote_firmware_dir}/firmware_latest.bin")

# Update ota_meta.json
meta_data = {
    "latest_file": "firmware_latest.bin",
    "original_filename": "firmware_v3.3.5_earcons_full.bin",
    "version": "v3.3.5-earcons-full",
    "size_bytes": file_size,
    "size_mb": size_mb,
    "md5": md5_hash,
    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "download_url": "http://192.168.1.114:8765/api/ota/firmware/firmware_latest.bin",
    "available": True
}

with sftp.file(f"{remote_firmware_dir}/ota_meta.json", 'w') as f:
    json.dump(meta_data, f, indent=2)

sftp.close()

# Restart container
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart STDOUT:", stdout.read().decode('utf-8', errors='replace').strip())
ssh.close()

time.sleep(4)
ota_res = requests.get("http://192.168.1.114:8765/api/ota/status", timeout=10).json()
print("OTA Status on NAS:", ota_res.get('version'), ota_res.get('md5'))
