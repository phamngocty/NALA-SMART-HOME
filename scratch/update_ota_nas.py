import paramiko
import json
import time
import httpx

# 1. Update files on NAS
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)

new_meta = {
    "latest_file": "firmware_latest.bin",
    "original_filename": "firmware_v3.6.1.bin",
    "version": "v3.6.1",
    "size_bytes": 1555072,
    "size_mb": 1.48,
    "md5": "d4d97e61ebc702e15ab2dc06015fac6d",
    "upload_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    "download_url": "http://192.168.1.114:8765/api/ota/firmware/firmware_latest.bin"
}

meta_str = json.dumps(new_meta, indent=2)
sftp = ssh.open_sftp()
with sftp.file("/home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware/ota_meta.json", "w") as f:
    f.write(meta_str)

# Copy to firmware_latest.bin
stdin, stdout, stderr = ssh.exec_command("cp /home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware/firmware_es3c28p.bin /home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware/firmware_latest.bin")
stdout.read()
ssh.close()
print("OTA meta and firmware_latest.bin updated successfully!")

# 2. Trigger OTA on both panels
with httpx.Client(timeout=10) as client:
    resp = client.get("http://192.168.1.114:8765/api/ota/status")
    print("OTA Status:", resp.json())
    
    # Start OTA for all devices
    start_resp = client.post("http://192.168.1.114:8765/api/ota/start", json={"target": "all"})
    print("OTA Start Response:", start_resp.json())
