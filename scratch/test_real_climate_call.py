import httpx

url = "http://192.168.1.114:8765/api/ha/call_service"
payload = {
    "domain": "climate",
    "service": "set_temperature",
    "entity_id": "climate.150633094640317_climate",
    "service_data": {
        "temperature": 25.0
    }
}

resp = httpx.post(url, json=payload, timeout=5.0)
print("Service call response:", resp.status_code, resp.json())
