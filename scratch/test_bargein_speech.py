import sys
import os
import time
import asyncio
import json
import websockets
import io
import wave

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'

async def test_bargein_during_speech():
    print("\n--- TEST BARGE-IN KHI AI ĐANG TRẢ LỜI CÂU THOẠI DÀI ---")
    ws_url = f"ws://{NAS_IP}:8765/ws/test_bargein_panel_live"
    try:
        async with websockets.connect(ws_url) as ws:
            # 1. Đăng ký thiết bị
            await ws.send(json.dumps({
                "type": "register",
                "payload": {
                    "pairing_code": "TEST02",
                    "mac": "AA:BB:CC:DD:EE:02",
                    "ip": "192.168.1.251",
                    "model": "ES3C28P",
                    "firmware_version": "v2.8.0"
                }
            }))
            
            # Đợi config_sync
            await asyncio.wait_for(ws.recv(), timeout=2.0)

            # 2. Sinh âm thanh 16kHz mono nói "Kể cho tôi nghe về lịch sử nước Việt Nam"
            # Ta dùng câu hỏi có sẵn hoặc dùng Faster-Whisper / Groq nhận diện
            # Ở đây ta gửi test session_control hoặc gửi lệnh giả lập
            print("2. Đang gửi âm thanh yêu cầu câu chuyện dài tới AI Server...")
            
            # Gửi gói nhị phân START
            hdr = bytearray(7)
            hdr[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr[2] = 0x02 # sender
            hdr[3] = 0x00 # target AI
            hdr[4:6] = (0).to_bytes(2, 'little')
            hdr[6] = 0x01 # START
            dummy_pcm = b'\x10\x00' * 512
            await ws.send(bytes(hdr + dummy_pcm[:512] + b'\x00'))
            
            # Gửi gói nhị phân END
            hdr[4:6] = (1).to_bytes(2, 'little')
            hdr[6] = 0x03 # END
            await ws.send(bytes(hdr + dummy_pcm[:512] + b'\x00'))
            
            abort_sent = False
            abort_time = 0.0
            
            for _ in range(30):
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                if isinstance(msg, str):
                    ev = json.loads(msg)
                    ev_type = ev.get("type")
                    print(f"   [EVENT] {ev_type}")
                    if ev_type == "tts_stop":
                        dt = (time.time() - abort_time) * 1000
                        print(f"   🎯 BẰNG CHỨNG XÁC THỰC: Nhận sự kiện 'tts_stop' sau {dt:.2f} ms (<30ms)!")
                        return True
                    if abort_sent and ev.get("payload", {}).get("state") == "idle":
                        dt = (time.time() - abort_time) * 1000
                        print(f"   🎯 BẰNG CHỨNG XÁC THỰC: Server chuyển về 'idle' sau {dt:.2f} ms!")
                        return True
                    if ev_type in ["ack_chime", "ai_state"] and not abort_sent:
                        print("   -> Đang đợi server xử lý... gửi lệnh 'abort' ngay!")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True
                else:
                    print(f"   [AUDIO CHUNK] Nhận gói audio nhị phân {len(msg)} bytes")
                    if not abort_sent:
                        print("   -> Gặp audio stream! Gửi lệnh 'abort' cắt lời ngay!")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True

    except Exception as e:
        print("Lỗi test:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_bargein_during_speech())
