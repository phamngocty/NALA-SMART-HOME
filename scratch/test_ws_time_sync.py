import asyncio
import json
import websockets
import time

async def test_ws():
    uri = "ws://192.168.1.114:8765/ws/test_panel_123"
    print("Connecting to", uri)
    async with websockets.connect(uri) as ws:
        # Send register message
        reg_msg = {
            "type": "register",
            "payload": {
                "pairing_code": "TEST99",
                "mac": "AA:BB:CC:DD:EE:FF",
                "ip": "192.168.1.200",
                "model": "ES3C28P",
                "firmware_version": "v3.3.4"
            }
        }
        await ws.send(json.dumps(reg_msg))
        print("Sent register message")

        # Wait for responses
        for _ in range(5):
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(resp)
                print("Received message type:", data.get("type"))
                if data.get("type") == "time_sync":
                    print("  -> time_sync epoch:", data.get("epoch"), "Current local time:", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data.get("epoch"))))
                elif data.get("type") == "config_sync":
                    print("  -> config_sync epoch:", data.get("epoch"))
                    break
            except asyncio.TimeoutError:
                break

        # Also test explicit get_time
        await ws.send(json.dumps({"type": "get_time"}))
        print("Sent get_time request")
        resp = await asyncio.wait_for(ws.recv(), timeout=3.0)
        data = json.loads(resp)
        print("Received response to get_time:", data.get("type"), "epoch:", data.get("epoch"))

asyncio.run(test_ws())
