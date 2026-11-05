"""
NALA SMART HOME - 1-CLICK BUILD & OTA DEPLOY SCRIPT
Biên dịch firmware từ máy tính, tự động tải lên NAS Hub và phát lệnh OTA tới tất cả màn hình.
Bạn chỉ cần chạy: python quick_ota_deploy.py
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FIRMWARE_DIR = os.path.join(PROJECT_DIR, "firmware_esp32s3_panel")
BIN_PATH = os.path.join(FIRMWARE_DIR, ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"

def run_step(title):
    print("\n" + "=" * 65)
    print(f"👉 {title}")
    print("=" * 65)

# BƯỚC 1: BIÊN DỊCH BẰNG PLATFORMIO
run_step("BƯỚC 1: Đang biên dịch firmware ESP32-S3 bằng PlatformIO...")
pio_cmd = "pio"
# Thử tìm platformio trong môi trường pio nếu có
pio_local = os.path.expanduser(r"~\.platformio\penv\Scripts\platformio.exe")
if os.path.exists(pio_local):
    pio_cmd = pio_local

try:
    ret = subprocess.run([pio_cmd, "run", "-d", FIRMWARE_DIR], check=True)
    print("✓ Biên dịch thành công!")
except Exception as e:
    print(f"❌ Lỗi biên dịch PlatformIO: {e}")
    sys.exit(1)

if not os.path.exists(BIN_PATH):
    print(f"❌ Không tìm thấy file firmware tại: {BIN_PATH}")
    sys.exit(1)

file_size_mb = round(os.path.getsize(BIN_PATH) / (1024 * 1024), 2)
print(f"✓ File firmware: {BIN_PATH} ({file_size_mb} MB)")

# BƯỚC 2: TẢI FILE .BIN LÊN NAS HUB
run_step(f"BƯỚC 2: Đang tải file firmware lên NAS Hub ({NAS_HUB_URL})...")
with open(BIN_PATH, "rb") as f:
    firmware_bytes = f.read()

version_tag = "v3.0.0"
filename = f"firmware_{version_tag.lower()}.bin"
upload_url = f"{NAS_HUB_URL}/api/ota/upload?filename={urllib.parse.quote(filename)}&version={urllib.parse.quote(version_tag)}"

req = urllib.request.Request(
    upload_url,
    data=firmware_bytes,
    headers={
        "Content-Type": "application/octet-stream",
        "X-Filename": filename,
        "X-Version": version_tag
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=15) as res:
        data = json.loads(res.read().decode("utf-8"))
        print(f"✓ {data.get('message', 'Tải lên thành công!')}")
except Exception as e:
    print(f"❌ Lỗi khi tải firmware lên NAS Hub: {e}")
    sys.exit(1)

# BƯỚC 3: PHÁT LỆNH OTA TỚI TẤT CẢ MÀN HÌNH
run_step("BƯỚC 3: Phát lệnh cập nhật OTA tới tất cả màn hình trong nhà...")
ota_start_url = f"{NAS_HUB_URL}/api/ota/start"
payload = json.dumps({"target": "all"}).encode("utf-8")

req_ota = urllib.request.Request(
    ota_start_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req_ota, timeout=10) as res:
        ota_res = json.loads(res.read().decode("utf-8"))
        print(f"🎉 THÀNH CÔNG: {ota_res.get('message')}")
        print("Màn hình sẽ hiển thị thanh tiến độ tiếng Việt và tự khởi động lại!")
except Exception as e:
    print(f"❌ Lỗi phát lệnh OTA: {e}")

print("=" * 65 + "\n")
