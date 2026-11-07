import asyncio
import json
import websockets

async def test():
    uri = "ws://192.168.1.114:8765/ws/default_panel"
    try:
        async with websockets.connect(uri) as ws:
            reg = {
                "type": "register",
                "payload": {
                    "mac": "00:11:22:33:44:99",
                    "pairing_code": "TEST1",
                    "ip": "192.168.1.99",
                    "model": "ES3C28P",
                    "room": "Phòng Thử Nghiệm",
                    "firmware_version": "v3.3.6",
                    "settings": {
                        "brightness": 100,
                        "volume": 80,
                        "mic_gain": 4,
                        "ring_on_call": False
                    }
                }
            }
            await ws.send(json.dumps(reg))
            print("Sent registration for TEST1")

            for i in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg, str):
                    data = json.loads(msg)
                    print(f"[{i}] Received: type={data.get('type')}, len={len(msg)} bytes")
                    if data.get('type') == 'config_sync':
                        payload = data.get('payload', {})
                        print("=== CONFIG_SYNC SUMMARY ===")
                        for k, v in payload.items():
                            val_str = json.dumps(v, ensure_ascii=False)
                            print(f"  '{k}': {len(val_str)} bytes")
                else:
                    print(f"[{i}] Binary msg: {len(msg)}")

            print("Sleeping 5 seconds to test stability...")
            await asyncio.sleep(5)
            print("Still alive and stable!")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
