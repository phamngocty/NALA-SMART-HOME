import sys
sys.stdout.reconfigure(encoding='utf-8')

import urllib.request
import urllib.parse
import json
import os
import hashlib

BIN_PATH = 'firmware_esp32s3_panel/.pio/build/esp32s3_panel/firmware.bin'
NAS_HUB_URL = 'http://192.168.1.114:8765'
version_tag = 'v3.2.0'
filename = f'firmware_{version_tag.lower()}.bin'

with open(BIN_PATH, 'rb') as f:
    firmware_bytes = f.read()

size_bytes = len(firmware_bytes)
size_mb = round(size_bytes / (1024 * 1024), 2)
md5_hash = hashlib.md5(firmware_bytes).hexdigest()

print(f"Firmware: {filename} ({size_mb} MB, MD5: {md5_hash})")

# Bước 1: Tải lên NAS
print(f"1. Đang tải lên NAS Hub ({NAS_HUB_URL})...")
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

with urllib.request.urlopen(req, timeout=15) as res:
    data = json.loads(res.read().decode("utf-8"))
    print("   Upload:", data.get("status"), "-", data.get("message"))

# Bước 2: Kiểm tra status trên NAS
with urllib.request.urlopen(f"{NAS_HUB_URL}/api/ota/status", timeout=5) as res:
    status_data = json.loads(res.read().decode("utf-8"))
    print("   NAS OTA Status:", status_data.get("latest_file"), "| Version:", status_data.get("version"), "| MD5:", status_data.get("md5"))

# Bước 3: Phát lệnh OTA tới tất cả màn hình
print("2. Đang phát lệnh OTA cập nhật tới tất cả màn hình...")
req_ota = urllib.request.Request(
    f"{NAS_HUB_URL}/api/ota/start",
    data=json.dumps({"target": "all"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

with urllib.request.urlopen(req_ota, timeout=10) as res:
    ota_res = json.loads(res.read().decode("utf-8"))
    print("   Kết quả OTA:", ota_res.get("status"), "-", ota_res.get("message"))

print("\n🎉 HOÀN TẤT PHÁT HÀNH BẢN CẬP NHẬT OTA V3.2.0!")
