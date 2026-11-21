import paramiko
import time
import sys
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_PORT = 8765

print("=== 1. KẾT NỐI SSH TỚI NAS VÀ TẢI TẤT CẢ FILE CẬP NHẬT ===")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username='nas152', password='271000', timeout=10)

files_to_upload = [
    ("server_nas_hub/app/voiceprint_manager.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/voiceprint_manager.py"),
    ("server_nas_hub/app/main_ws_server.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py"),
    ("server_nas_hub/app/automation_engine.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/automation_engine.py"),
    ("server_nas_hub/app/static/index.html", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html"),
]

sftp = ssh.open_sftp()
for loc, rem in files_to_upload:
    print(f"Uploading {loc} -> {rem}...")
    sftp.put(loc, rem)
sftp.close()

print("\n=== 2. KHỞI ĐỘNG LẠI CONTAINER NALA_NAS_WS_HUB ===")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart output:", stdout.read().decode().strip())

print("\nChờ 6 giây để container và CAM++ model sẵn sàng...")
time.sleep(6)

print("\n=== 3. KIỂM TRA DOCKER LOGS MỚI NHẤT ===")
stdin, stdout, stderr = ssh.exec_command('docker logs --tail 35 nala_nas_ws_hub')
logs = stdout.read().decode('utf-8', errors='replace')
print(logs)

ssh.close()

print("\n=== 4. TEST INTEGRATION CÁC API TRÊN NAS HUB (http://192.168.1.114:8765) ===")

# Test 1: Speakers list
try:
    req = urllib.request.Request(f'http://{NAS_IP}:{NAS_PORT}/api/voiceprint/speakers')
    res = urllib.request.urlopen(req, timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    print(f"[TEST 1 - GET /api/voiceprint/speakers]: Status={body.get('status')} - Speakers={len(body.get('speakers', []))}")
except Exception as e:
    print(f"[TEST 1 ERROR]: {e}")

# Test 2: Automations list
try:
    req = urllib.request.Request(f'http://{NAS_IP}:{NAS_PORT}/api/automations')
    res = urllib.request.urlopen(req, timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    print(f"[TEST 2 - GET /api/automations]: Status={body.get('status')} - Rules={len(body.get('rules', []))}")
except Exception as e:
    print(f"[TEST 2 ERROR]: {e}")

# Test 3: History list
try:
    req = urllib.request.Request(f'http://{NAS_IP}:{NAS_PORT}/api/history?limit=10')
    res = urllib.request.urlopen(req, timeout=5)
    body = json.loads(res.read().decode('utf-8'))
    records = body.get('records', [])
    print(f"[TEST 3 - GET /api/history]: Status={body.get('status')} - Records={len(records)}")
    
    # Test 4: XiaoZhi Multi-enrollment with existing history file (if any exists)
    audio_records = [r for r in records if r.get('audio_file')]
    if audio_records:
        test_fn = audio_records[0]['audio_file']
        print(f"Thử nghiệm đăng ký vân giọng từ file lịch sử {test_fn}...")
        enroll_data = json.dumps({
            "speaker_name": "Test_Xiaozhi",
            "filenames": [test_fn]
        }).encode('utf-8')
        enroll_req = urllib.request.Request(
            f'http://{NAS_IP}:{NAS_PORT}/api/voiceprint/enroll',
            data=enroll_data,
            headers={'Content-Type': 'application/json'}
        )
        enroll_res = urllib.request.urlopen(enroll_req, timeout=8)
        enroll_body = json.loads(enroll_res.read().decode('utf-8'))
        print(f"[TEST 4 - POST /api/voiceprint/enroll (XiaoZhi filenames)]: {enroll_body}")
        
        # Cleanup test speaker
        del_req = urllib.request.Request(
            f'http://{NAS_IP}:{NAS_PORT}/api/voiceprint/speakers/Test_Xiaozhi',
            method='DELETE'
        )
        del_res = urllib.request.urlopen(del_req, timeout=5)
        print(f"[TEST 4 CLEANUP]: Status={del_res.status}")
    else:
        print("Không có file âm thanh lịch sử để test enrollment, nhưng API đã sẵn sàng.")
except Exception as e:
    print(f"[TEST 3/4 ERROR]: {e}")

# Test 5: Verify static index.html version header
try:
    req = urllib.request.Request(f'http://{NAS_IP}:{NAS_PORT}/')
    res = urllib.request.urlopen(req, timeout=5)
    html = res.read().decode('utf-8')
    if 'TARGET_VER = "v3.0.6"' in html:
        print("✅ [TEST 5 - WEB ADMIN INDEX.HTML]: Đã xác nhận v3.0.6 (XiaoZhi Multi-Sample & History Multi-Select) đang chạy live!")
    else:
        print("⚠️ [TEST 5]: Không thấy TARGET_VER = 'v3.0.6' trong index.html")
except Exception as e:
    print(f"[TEST 5 ERROR]: {e}")
