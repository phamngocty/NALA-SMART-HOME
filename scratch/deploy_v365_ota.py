import os
import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
BIN_PATH = os.path.join("firmware_esp32s3_panel", ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"
version_tag = "v3.6.5"
filename = f"firmware_{version_tag.lower()}.bin"

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
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode('utf-8'))
    print("Upload result:", res)

# Trigger OTA for 881C
start_req = urllib.request.Request(
    f"{NAS_HUB_URL}/api/ota/start",
    data=json.dumps({"device_code": "881C"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(start_req) as resp:
    start_res = json.loads(resp.read().decode("utf-8"))
    print("OTA Start Result:", start_res)
