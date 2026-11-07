import os
import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
BIN_PATH = os.path.join("firmware_esp32s3_panel", ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"
version_tag = "v3.4.3"
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

print("Triggering OTA for Panel 881C (Room Ty)...")
ota_start_url = f"{NAS_HUB_URL}/api/ota/start"
payload = json.dumps({"target": "881C", "firmware_filename": "firmware_latest.bin"}).encode("utf-8")
req_start = urllib.request.Request(
    ota_start_url,
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req_start, timeout=10) as resp:
        res_start = json.loads(resp.read().decode('utf-8'))
        print("OTA Start result for 881C:", res_start)
except Exception as e:
    print(f"Trigger OTA failed: {e}")
