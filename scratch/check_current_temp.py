import httpx
resp = httpx.get("http://192.168.1.114:8765/api/ha/entities")
for e in resp.json():
    if e.get("entity_id") == "climate.150633094640317_climate":
        print("Updated state in HA:")
        print("State:", e.get("state"))
        print("Target Temperature:", e.get("attributes", {}).get("temperature"))
        print("Current Temperature:", e.get("attributes", {}).get("current_temperature"))
