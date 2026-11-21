import paramiko
import time
import sys
import urllib.request
import json

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

files_to_upload = [
    ("server_nas_hub/app/automation_engine.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/automation_engine.py"),
    ("server_nas_hub/app/main_ws_server.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py"),
    ("server_nas_hub/app/static/index.html", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html"),
]

print("=== BẮT ĐẦU TẢI LÊN MÁY CHỦ NAS HUB ===")
sftp = ssh.open_sftp()
for loc, rem in files_to_upload:
    print(f"Uploading {loc} -> {rem}...")
    sftp.put(loc, rem)
sftp.close()

print("\n=== RESTART CONTAINER NALA_NAS_WS_HUB ===")
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print("Restart output:", stdout.read().decode().strip())

print("\nChờ 5s để container khởi động...")
time.sleep(5)

ssh.close()

print("\n=== KIỂM THỬ CÁC TÍNH NĂNG TỰ ĐỘNG HÓA TÙY BIẾN ===")

# 1. Test GET rules
req = urllib.request.urlopen("http://192.168.1.114:8765/api/automations", timeout=5)
data = json.loads(req.read().decode())
print(f"1. GET /api/automations: {len(data.get('rules', []))} rules hiện có.")

# 2. Test POST create custom rule
custom_rule = {
    "name": "Kịch bản thử nghiệm phòng khách",
    "description": "Thử nghiệm tạo kịch bản tùy ý từ Web Admin",
    "enabled": False,
    "trigger": {
        "type": "living_context",
        "state": "deep_sleep"
    },
    "conditions": {
        "target_room": "Phòng khách",
        "time_range": {"start": "23:00", "end": "05:00"},
        "max_lux": 20
    },
    "actions": [
        {"domain": "climate", "service": "set_temperature", "data": {"temperature": 27.0}},
        {"domain": "light", "service": "turn_off"}
    ]
}

post_req = urllib.request.Request(
    "http://192.168.1.114:8765/api/automations",
    data=json.dumps(custom_rule).encode(),
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(post_req, timeout=5)
created = json.loads(res.read().decode()).get("rule", {})
rule_id = created.get("id")
print(f"2. POST /api/automations: Tạo thành công rule_id = {rule_id}")

# 3. Test toggle without payload
toggle_req = urllib.request.Request(
    f"http://192.168.1.114:8765/api/automations/{rule_id}/toggle",
    data=b"{}",
    headers={"Content-Type": "application/json"}
)
res = urllib.request.urlopen(toggle_req, timeout=5)
toggle_res = json.loads(res.read().decode())
print(f"3. POST toggle: trạng thái mới = {toggle_res.get('enabled')}")

# 4. Test PUT update rule
custom_rule["name"] = "Kịch bản đã sửa đổi nhiệt độ 28"
custom_rule["actions"][0]["data"]["temperature"] = 28.0
put_req = urllib.request.Request(
    f"http://192.168.1.114:8765/api/automations/{rule_id}",
    data=json.dumps(custom_rule).encode(),
    headers={"Content-Type": "application/json"},
    method="PUT"
)
res = urllib.request.urlopen(put_req, timeout=5)
updated = json.loads(res.read().decode()).get("rule", {})
print(f"4. PUT /api/automations/{rule_id}: Sửa thành công: name = {updated.get('name')}")

# 5. Test DELETE rule
del_req = urllib.request.Request(
    f"http://192.168.1.114:8765/api/automations/{rule_id}",
    method="DELETE"
)
res = urllib.request.urlopen(del_req, timeout=5)
del_res = json.loads(res.read().decode())
print(f"5. DELETE /api/automations/{rule_id}: {del_res.get('message')}")

print("\n=== TẤT CẢ CÁC API TỰ ĐỘNG HÓA TÙY BIẾN HOẠT ĐỘNG HOÀN HẢO! ===")
