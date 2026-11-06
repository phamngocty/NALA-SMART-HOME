import httpx
import os

fw_path = "firmware_esp32s3_panel/.pio/build/esp32s3_panel/firmware.bin"
if os.path.exists(fw_path):
    size = os.path.getsize(fw_path)
    print(f"Uploading firmware.bin ({size} bytes) to NAS Hub OTA...")
    with open(fw_path, "rb") as f:
        content = f.read()
    headers = {
        "x-filename": "firmware_v3.3.1_chime.bin",
        "x-version": "v3.3.1-chime",
        "content-type": "application/octet-stream"
    }
    resp = httpx.post("http://192.168.1.114:8765/api/ota/upload", content=content, headers=headers, timeout=30.0)
    print("Upload response:", resp.status_code, resp.text)
else:
    print("Firmware file not found at", fw_path)
