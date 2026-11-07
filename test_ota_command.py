import urllib.request
import urllib.parse
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')
NAS_HUB_URL = "http://192.168.1.114:8765"

print("1. Testing GET /api/ota/status...")
try:
    with urllib.request.urlopen(f"{NAS_HUB_URL}/api/ota/status", timeout=5) as resp:
        print("OTA Status:", json.loads(resp.read().decode('utf-8')))
except Exception as e:
    print("GET /api/ota/status failed:", e)

print("\n2. Testing POST /api/ota/start with target='all'...")
payload = json.dumps({"target": "all", "firmware_filename": "firmware_latest.bin"}).encode("utf-8")
req = urllib.request.Request(
    f"{NAS_HUB_URL}/api/ota/start",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("OTA Start 'all' result:", json.loads(resp.read().decode('utf-8')))
except Exception as e:
    if hasattr(e, 'read'):
        print("OTA Start 'all' failed:", e.read().decode('utf-8'))
    else:
        print("OTA Start 'all' failed:", e)

print("\n3. Testing GET /api/ota/firmware/non_existent.bin fallback...")
try:
    req_file = urllib.request.Request(f"{NAS_HUB_URL}/api/ota/firmware/non_existent.bin", method="HEAD")
    with urllib.request.urlopen(req_file, timeout=5) as resp:
        print("Fallback test status:", resp.status, "Content-Length:", resp.headers.get("Content-Length"))
except Exception as e:
    print("Fallback test failed:", e)
