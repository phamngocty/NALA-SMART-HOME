import httpx
import json

url = "http://192.168.1.114:8765/api/ha/call_service"
payload = {
    "domain": "climate",
    "service": "set_temperature",
    "entity_id": "climate.150633094640317_climate",
    "service_data": {
        "temperature": 26.0
    }
}

resp = httpx.post(url, json=payload, timeout=5.0)
print("Response:", resp.status_code, resp.text)
