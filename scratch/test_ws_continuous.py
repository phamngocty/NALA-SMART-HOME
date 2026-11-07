import sys
import time
import json
import asyncio
import websockets

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'

async def test_ws_speech_to_start_listen():
    print("\n--- TEST WS: NÓI THOẠI -> TTS HOÀN TẤT -> SERVER GỬI START_LISTEN ---")
    ws_url = f"ws://{NAS_IP}:8765/ws/TEST_CONTINUOUS_PANEL"
    
    # 1. Sinh âm thanh nói "Bật đèn ngủ"
    import urllib.request
    chat_url = f"http://{NAS_IP}:8765/api/ai/chat"
    req_body = json.dumps({"message": "nói xin chào", "provider": "gemini"}).encode('utf-8')
    req = urllib.request.Request(chat_url, data=req_body, headers={'Content-Type': 'application/json'})
    import base64
    with urllib.request.urlopen(req) as r:
        d = json.loads(r.read().decode('utf-8'))
        wav_b64 = d.get("audio_wav_base64", "")
        wav_bytes = base64.b64decode(wav_b64)
        # Bỏ 44 bytes header WAV để lấy PCM 16kHz
        pcm_data = wav_bytes[44:44+16000*2] # 1 giây âm thanh

    async with websockets.connect(ws_url) as ws:
        # Register
        await ws.send(json.dumps({
            "type": "register",
            "payload": {
                "pairing_code": "TEST_CP2",
                "mac": "AA:BB:CC:99:99:98",
                "ip": "192.168.1.241",
                "model": "ES3C28P",
                "firmware_version": "v3.3.5"
            }
        }))
        res = await asyncio.wait_for(ws.recv(), timeout=2.0)
        print("1. Registered device.")

        # Gửi audio PCM
        seq = 0
        chunk_size = 512
        for i in range(0, len(pcm_data), chunk_size):
            chunk = pcm_data[i:i+chunk_size]
            hdr = bytearray(7)
            hdr[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr[2] = 0x01 # sender
            hdr[3] = 0x00 # target AI
            hdr[4:6] = seq.to_bytes(2, 'little')
            hdr[6] = 0x01 if seq == 0 else 0x02
            padding = b'\x00' * (512 - len(chunk))
            pkt = bytes(hdr + chunk + padding + b'\x00') # 7 + 512 + 1 = 520 bytes!
            await ws.send(pkt)
            seq += 1
            await asyncio.sleep(0.01)

        # Gói kết thúc
        hdr_end = bytearray(7)
        hdr_end[0:2] = (0xA55A).to_bytes(2, 'little')
        hdr_end[2] = 0x01
        hdr_end[3] = 0x00
        hdr_end[4:6] = seq.to_bytes(2, 'little')
        hdr_end[6] = 0x03 # STREAM_FLAG_END
        pkt_end = bytes(hdr_end + b'\x00'*512 + b'\x00') # 520 bytes
        await ws.send(pkt_end)
        print("2. Sent audio stream with STREAM_FLAG_END (520 bytes).")

        got_start_listen = False
        t_start = time.time()
        while time.time() - t_start < 12.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
            except asyncio.TimeoutError:
                break
            if isinstance(raw, str):
                ev = json.loads(raw)
                ev_type = ev.get("type")
                if ev_type in ["ai_state", "start_listen", "sentence_start"]:
                    print(f"   [EVENT] {ev_type}: {ev}")
                if ev_type == "start_listen":
                    got_start_listen = True
                    print(f"\n   🌟 XÁC NHẬN HOÀN HẢO! Server đã bắn lệnh 'start_listen' với timeout={ev['payload']['timeout_ms']}ms!")
                    break

        assert got_start_listen, "Expected start_listen event after TTS!"
        print("3. Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_ws_speech_to_start_listen())
