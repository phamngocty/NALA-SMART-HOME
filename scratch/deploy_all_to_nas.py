import os
import hashlib
import json
import time
import paramiko

NAS_HOST = '192.168.1.114'
NAS_USER = 'nas152'
NAS_PASS = '271000'

fw_local = r'c:\Users\phamn\Documents\PlatformIO\NALA SMART HOME\firmware_esp32s3_panel\.pio\build\esp32s3_panel\firmware.bin'
app_dir = r'c:\Users\phamn\Documents\PlatformIO\NALA SMART HOME\server_nas_hub\app'
remote_app_dir = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app'

fw_size = os.path.getsize(fw_local)
with open(fw_local, 'rb') as f:
    fw_md5 = hashlib.md5(f.read()).hexdigest()

print(f"Firmware binary: size={fw_size} bytes, md5={fw_md5}")

ota_meta = {
    "version": "v3.3.6",
    "filename": "firmware_latest.bin",
    "size_bytes": fw_size,
    "md5": fw_md5,
    "release_date": time.strftime("%Y-%m-%d %H:%M:%S"),
    "release_notes": "Bản firmware v3.3.6 chuẩn hóa: Tối ưu bộ nhớ cho ESP32-S3 Zero PSRAM, loại bỏ Opus codec để giải phóng 38KB SRAM, chuyển sang Raw PCM 520 bytes ổn định tuyệt đối, lọc tinh gọn gói HA State và All-Rooms chống tràn bộ đệm WebSocket, chấm dứt hoàn toàn hiện tượng reconnect loop."
}

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_HOST, username=NAS_USER, password=NAS_PASS)
sftp = ssh.open_sftp()

files_to_sync = [
    ('static/index.html', f'{remote_app_dir}/static/index.html'),
    ('main_ws_server.py', f'{remote_app_dir}/main_ws_server.py'),
    ('history_manager.py', f'{remote_app_dir}/history_manager.py'),
    ('ai_agent_router.py', f'{remote_app_dir}/ai_agent_router.py'),
    ('intercom_router.py', f'{remote_app_dir}/intercom_router.py'),
    ('stt_tts_pipeline.py', f'{remote_app_dir}/stt_tts_pipeline.py'),
    ('wake_word_manager.py', f'{remote_app_dir}/wake_word_manager.py'),
]

for local_rel, remote_p in files_to_sync:
    local_p = os.path.join(app_dir, local_rel)
    if os.path.exists(local_p):
        print(f"Uploading {local_rel}...")
        sftp.put(local_p, remote_p)

print("Uploading firmware binaries...")
sftp.put(fw_local, f'{remote_app_dir}/firmware/firmware_latest.bin')
sftp.put(fw_local, f'{remote_app_dir}/firmware/firmware_es3c28p.bin')
sftp.put(fw_local, f'{remote_app_dir}/firmware/firmware_v3.3.6.bin')

print("Updating ota_meta.json...")
with sftp.file(f'{remote_app_dir}/firmware/ota_meta.json', 'w') as f:
    f.write(json.dumps(ota_meta, indent=2, ensure_ascii=False))

sftp.close()

print("Restarting nala_nas_ws_hub container...")
_, stdout, stderr = ssh.exec_command('echo 271000 | sudo -S docker restart nala_nas_ws_hub')
print("Restart STDOUT:", stdout.read().decode('utf-8', errors='replace'))
print("Restart STDERR:", stderr.read().decode('utf-8', errors='replace'))

time.sleep(4)
print("Verifying logs...")
_, stdout, _ = ssh.exec_command('echo 271000 | sudo -S docker logs --tail 30 nala_nas_ws_hub 2>&1')
print(stdout.read().decode('utf-8', errors='replace'))

ssh.close()
print("Deploy completed successfully!")
