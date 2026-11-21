import os
import shutil
import urllib.request
import urllib.parse
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
BIN_PATH = os.path.join("firmware_esp32s3_panel", ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"
version_tag = "v3.6.9"
filename = f"firmware_{version_tag.lower()}.bin"

if not os.path.exists(BIN_PATH):
    print(f"ERROR: File not found: {BIN_PATH}")
    sys.exit(1)

# Sao lưu cục bộ
os.makedirs("release", exist_ok=True)
os.makedirs("docs/firmware", exist_ok=True)
shutil.copyfile(BIN_PATH, "release/firmware.bin")
shutil.copyfile(BIN_PATH, f"docs/firmware/{filename}")
shutil.copyfile(BIN_PATH, "docs/firmware/firmware.bin")
print(f"Copied firmware to release/firmware.bin and docs/firmware/{filename}")

print(f"Reading {BIN_PATH}...")
with open(BIN_PATH, "rb") as f:
    firmware_bytes = f.read()

print(f"Uploading {filename} ({len(firmware_bytes)} bytes) to {NAS_HUB_URL}...")
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Upload result:", res)
except Exception as e:
    print(f"Upload failed: {e}")
    sys.exit(1)

targets = ["881C"]
for target_id in targets:
    print(f"\nTriggering OTA for Panel {target_id}...")
    ota_start_url = f"{NAS_HUB_URL}/api/ota/start"
    payload = json.dumps({"target": target_id, "firmware_filename": "firmware_latest.bin"}).encode("utf-8")
    req_start = urllib.request.Request(
        ota_start_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req_start, timeout=10) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print("OTA Start result:", res)
    except Exception as e:
        print(f"OTA start failed: {e}")

print("\nMonitoring OTA status...")
for i in range(25):
    time.sleep(2)
    try:
        with urllib.request.urlopen(f"{NAS_HUB_URL}/api/ota/status", timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            t_status = data.get("in_progress", {}).get("881C") or data.get("history", [{}])[0]
            pct = t_status.get("progress_pct", 0)
            st = t_status.get("status", "unknown")
            print(f"[{i*2}s] 881C Status: {st} - Progress: {pct}%")
            if st == "completed" or (st == "success" and pct == 100):
                print("\nOTA HOÀN TẤT THÀNH CÔNG 100%!")
                break
    except Exception as e:
        print(f"Error checking status: {e}")

print("\nKiểm tra trạng thái thiết bị...")
time.sleep(3)
try:
    with urllib.request.urlopen(f"{NAS_HUB_URL}/api/devices", timeout=5) as resp:
        devs = json.loads(resp.read().decode('utf-8'))
        for d in devs:
            if d.get("pairing_code") == "881C":
                print(f"Panel 881C: Online={d.get('online')} | FW={d.get('firmware_version')} | Radar={d.get('radar')} | Context={d.get('living_context')}")
except Exception as e:
    print(f"Error checking devices: {e}")
