import sys
import time
import json
import urllib.request
import asyncio
import websockets

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'

def test_api_config():
    print("\n--- 1. TEST /api/ai/config ---")
    url = f"http://{NAS_IP}:8765/api/ai/config"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as res:
        data = json.loads(res.read().decode('utf-8'))
        print("Continuous Conversation Enabled:", data.get("continuous_conversation"))
        print("Inactivity Timeout (ms):", data.get("continuous_timeout_ms"))
        print("Session Timeout (s):", data.get("session_timeout_seconds"))
        assert data.get("continuous_conversation") is True
        assert data.get("continuous_timeout_ms") == 8000
        print("✓ API Config check passed!")

def test_multi_turn_chat():
    print("\n--- 2. TEST MULTI-TURN CONTEXT MEMORY VIA /api/ai/chat ---")
    url = f"http://{NAS_IP}:8765/api/ai/chat"

    # Turn 1
    t1_payload = json.dumps({"message": "Bật máy lạnh phòng ngủ ty 26 độ", "provider": "gemini"}).encode('utf-8')
    req1 = urllib.request.Request(url, data=t1_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req1) as res:
        d1 = json.loads(res.read().decode('utf-8'))
        print("Turn 1 Reply:", d1.get("reply"))

    # Turn 2: Tiếp nối không nhắc tên thiết bị / phòng
    t2_payload = json.dumps({"message": "Hạ xuống 22 độ đi", "provider": "gemini"}).encode('utf-8')
    req2 = urllib.request.Request(url, data=t2_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req2) as res:
        d2 = json.loads(res.read().decode('utf-8'))
        print("Turn 2 Reply (Nhờ Ngữ Cảnh):", d2.get("reply"))

    # Turn 3: Chào tạm biệt
    t3_payload = json.dumps({"message": "Cảm ơn Nala nhé", "provider": "gemini"}).encode('utf-8')
    req3 = urllib.request.Request(url, data=t3_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req3) as res:
        d3 = json.loads(res.read().decode('utf-8'))
        print("Turn 3 Reply (Tạm biệt):", d3.get("reply"))

async def test_ws_auto_listen():
    print("\n--- 3. TEST WEBSOCKET START_LISTEN EVENT (XIAOZHI STYLE) ---")
    ws_url = f"ws://{NAS_IP}:8765/ws/TEST_CONTINUOUS_PANEL"
    try:
        async with websockets.connect(ws_url) as ws:
            # Gửi register
            await ws.send(json.dumps({
                "type": "register",
                "payload": {
                    "pairing_code": "TEST_CP",
                    "mac": "AA:BB:CC:99:99:99",
                    "ip": "192.168.1.240",
                    "model": "ES3C28P",
                    "firmware_version": "v3.3.5"
                }
            }))
            res = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print("Received register response.")

            # Giả lập gửi 0.5s audio PCM nói "Mấy giờ rồi"
            dummy_pcm = b'\x05\x00' * 8000 # 8000 samples = 0.5s
            
            # Gói 1: START
            hdr_start = bytearray(7)
            hdr_start[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_start[2] = 0x01 # sender
            hdr_start[3] = 0x00 # target AI
            hdr_start[4:6] = (0).to_bytes(2, 'little')
            hdr_start[6] = 0x01 # START
            await ws.send(bytes(hdr_start + dummy_pcm[:512] + b'\x00'))

            # Gói 2: END
            hdr_end = bytearray(7)
            hdr_end[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_end[2] = 0x01
            hdr_end[3] = 0x00
            hdr_end[4:6] = (1).to_bytes(2, 'little')
            hdr_end[6] = 0x03 # END
            await ws.send(bytes(hdr_end + dummy_pcm[:512] + b'\x00'))
            print("Sent audio stream to AI.")

            got_start_listen = False
            t_start = time.time()
            while time.time() - t_start < 10.0:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                except asyncio.TimeoutError:
                    break

                if isinstance(msg, str):
                    ev = json.loads(msg)
                    ev_type = ev.get("type")
                    if ev_type in ["ai_state", "start_listen", "sentence_start"]:
                        print(f"   [WS EVENT] {ev_type}: {ev}")
                    if ev_type == "start_listen":
                        got_start_listen = True
                        print(f"\n   🌟 THÀNH CÔNG! Server đã gửi lệnh 'start_listen' với timeout {ev.get('payload', {}).get('timeout_ms')}ms!")
                        break

            assert got_start_listen, "Expected start_listen event after TTS finished!"
    except Exception as e:
        print("WS Test error:", e)

if __name__ == "__main__":
    test_api_config()
    test_multi_turn_chat()
    asyncio.run(test_ws_auto_listen())
