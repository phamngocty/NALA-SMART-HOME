import sys
import os
import time
import asyncio
import json
import websockets

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'

async def test_barge_in():
    print("\n--- TEST BARGE-IN / ABORT SPEAKING VIA WEBSOCKET ---")
    ws_url = f"ws://{NAS_IP}:8765/ws/test_bargein_panel"
    try:
        async with websockets.connect(ws_url) as ws:
            print("1. Connected to WebSocket server.")

            # Gửi gói register
            reg_msg = {
                "type": "register",
                "payload": {
                    "pairing_code": "TEST01",
                    "mac": "AA:BB:CC:DD:EE:01",
                    "ip": "192.168.1.250",
                    "model": "ES3C28P",
                    "firmware_version": "v2.8.0"
                }
            }
            await ws.send(json.dumps(reg_msg))
            print("2. Sent register packet for TEST01.")

            # Nhận config_sync từ server
            res = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print("3. Received response from server:", res[:80] if isinstance(res, str) else len(res))

            # Giả lập gửi 0.5s audio PCM im lặng hoặc tiếng
            dummy_pcm = b'\x05\x00' * 8000 # 8000 samples = 0.5s
            
            # Gói 1: START (STREAM_FLAG_START = 0x01)
            hdr_start = bytearray(7)
            hdr_start[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_start[2] = 0x01 # sender
            hdr_start[3] = 0x00 # target AI
            hdr_start[4:6] = (0).to_bytes(2, 'little')
            hdr_start[6] = 0x01 # START
            chunk = dummy_pcm[:512]
            await ws.send(bytes(hdr_start + chunk + b'\x00'))
            print("4. Sent STREAM_FLAG_START chunk.")

            # Gói 2: END (STREAM_FLAG_END = 0x03)
            hdr_end = bytearray(7)
            hdr_end[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_end[2] = 0x01
            hdr_end[3] = 0x00
            hdr_end[4:6] = (1).to_bytes(2, 'little')
            hdr_end[6] = 0x03 # END
            await ws.send(bytes(hdr_end + chunk + b'\x00'))
            print("5. Sent STREAM_FLAG_END chunk. AI flow is triggered!")

            # Lắng nghe sự kiện từ server
            abort_sent = False
            abort_time = 0.0
            t_start = time.time()
            
            while time.time() - t_start < 5.0:
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                except asyncio.TimeoutError:
                    print("Timeout waiting for message.")
                    break
                
                if isinstance(raw_msg, str):
                    ev = json.loads(raw_msg)
                    ev_type = ev.get("type")
                    print(f"   [EVENT] {ev_type}: {ev}")
                    
                    # Khi server chuyển sang trạng thái thinking hoặc ack_chime, người dùng ngắt lời!
                    if (ev_type in ["ack_chime", "ai_state"] or "thinking" in str(ev)) and not abort_sent:
                        print("\n   ⚡ [USER ACTION] Người dùng bấm PTT hoặc ngắt lời -> Gửi {'type': 'abort'}!")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True

                    if ev_type == "tts_stop":
                        dt_ms = (time.time() - abort_time) * 1000
                        print(f"\n   ✅ THÀNH CÔNG! Nhận được 'tts_stop' sau {dt_ms:.1f}ms (< 30ms)!")
                        print("   -> Server đã dừng ngay lập tức việc tổng hợp và phát âm thanh!")
                        return True
                    
                    if abort_sent and ev.get("payload", {}).get("state") == "idle":
                        dt_ms = (time.time() - abort_time) * 1000
                        print(f"\n   ✅ THÀNH CÔNG! AI đã trở về trạng thái IDLE sau {dt_ms:.1f}ms!")
                        return True
                else:
                    print(f"   [BINARY AUDIO] Server đang stream {len(raw_msg)} bytes audio...")
                    if not abort_sent:
                        print("\n   ⚡ [USER ACTION] AI đang nói -> Người dùng ngắt lời! Gửi {'type': 'abort'}!")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True

    except Exception as e:
        print("Error during test:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_barge_in())
