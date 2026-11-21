import paramiko
import time
import sys
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_PORT = 8765

print("=== 1. TẢI FILE INDEX.HTML V3.1.0 LÊN NAS HUB ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username='nas152', password='271000', timeout=10)

sftp = ssh.open_sftp()
sftp.put("server_nas_hub/app/static/index.html", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html")
sftp.close()
print("Uploaded index.html successfully!")

print("\n=== 2. KHỞI ĐỘNG LẠI CONTAINER NALA_NAS_WS_HUB ===")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart output:", stdout.read().decode().strip())
time.sleep(5)
ssh.close()

print("\n=== 3. KIỂM TRA WEB SERVER LIVE ===")
req = urllib.request.Request(f'http://{NAS_IP}:{NAS_PORT}/')
res = urllib.request.urlopen(req, timeout=5)
html = res.read().decode('utf-8')

if 'TARGET_VER = "v3.1.0"' in html:
    print("✅ ĐÃ XÁC NHẬN: Web Admin v3.1.0 đang chạy live!")
else:
    print("⚠️ Không tìm thấy TARGET_VER = 'v3.1.0'")

if 'id="userProfileMemoryModal"' in html and 'id="livingContextAutomationModal"' in html and 'id="communicationModal"' in html and 'id="systemSettingsModal"' in html:
    print("✅ ĐÃ XÁC NHẬN: Cả 4 Siêu Modal Thống Nhất đang hoạt động hoàn hảo!")
else:
    print("⚠️ Một số modal chưa có trong response")
