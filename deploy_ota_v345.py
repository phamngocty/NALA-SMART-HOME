import os
import urllib.request
import urllib.parse
import json
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
BIN_PATH = os.path.join("firmware_esp32s3_panel", ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"
version_tag = "v3.4.5"
filename = f"firmware_{version_tag.lower()}.bin"

if not os.path.exists(BIN_PATH):
    print(f"ERROR: File not found: {BIN_PATH}")
    sys.exit(1)

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

for target_id in ["881C", "D6F4"]:
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
            res_start = json.loads(resp.read().decode('utf-8'))
            print(f"OTA Start result for {target_id}:", res_start)
    except Exception as e:
        print(f"Trigger OTA failed for {target_id}: {e}")

print("\nMonitoring OTA progress on Panels for 30 seconds...")
for i in range(15):
    time.sleep(2)
    try:
        req_dev = urllib.request.Request(f"{NAS_HUB_URL}/api/devices")
        with urllib.request.urlopen(req_dev, timeout=5) as r:
            devs = json.loads(r.read().decode('utf-8'))
            dev_881c = devs.get("881C", {})
            dev_d6f4 = devs.get("D6F4", {})
            ota_881c = dev_881c.get("ota", {})
            ota_d6f4 = dev_d6f4.get("ota", {})
            print(f"[{i*2}s] 881C: Online={dev_881c.get('online')} Ver={dev_881c.get('firmware_version')} OTA={ota_881c.get('progress')}% | D6F4: Online={dev_d6f4.get('online')} Ver={dev_d6f4.get('firmware_version')} OTA={ota_d6f4.get('progress')}%")
            if dev_881c.get("firmware_version") == version_tag and dev_d6f4.get("firmware_version") == version_tag:
                print(f">>> All Panels successfully upgraded to {version_tag}!")
                break
    except Exception as e:
        print(f"Check status error: {e}")
