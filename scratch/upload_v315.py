import os
import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
BIN_PATH = os.path.join("firmware_esp32s3_panel", ".pio", "build", "esp32s3_panel", "firmware.bin")
NAS_HUB_URL = "http://192.168.1.114:8765"
version_tag = "v3.1.5"
filename = "firmware_latest.bin"

print(f"Reading {BIN_PATH}...")
with open(BIN_PATH, "rb") as f:
    firmware_bytes = f.read()

print(f"Uploading {filename} ({len(firmware_bytes)} bytes) as version {version_tag} to {NAS_HUB_URL}...")
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

# Also upload as firmware_v3.1.5.bin for archive
filename_ver = f"firmware_{version_tag.lower()}.bin"
upload_url2 = f"{NAS_HUB_URL}/api/ota/upload?filename={urllib.parse.quote(filename_ver)}&version={urllib.parse.quote(version_tag)}"
req2 = urllib.request.Request(
    upload_url2,
    data=firmware_bytes,
    headers={
        "Content-Type": "application/octet-stream",
        "X-Filename": filename_ver,
        "X-Version": version_tag
    },
    method="POST"
)
with urllib.request.urlopen(req2) as resp:
    res2 = json.loads(resp.read().decode('utf-8'))
    print("Upload archive result:", res2)

print("NAS Hub firmware update completed!")
