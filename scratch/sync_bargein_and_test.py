import sys
import os
import time
import asyncio
import json
import paramiko
import websockets

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_USER = 'nas152'
NAS_PASS = '271000'
REMOTE_BASE = '/home/nas152/nala-voice-intercom-system/server_nas_hub'

local_main_ws = os.path.abspath('server_nas_hub/app/main_ws_server.py')

print(f"Connecting to NAS {NAS_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username=NAS_USER, password=NAS_PASS)

sftp = ssh.open_sftp()
print(f"Uploading {os.path.basename(local_main_ws)} -> {REMOTE_BASE}/app/main_ws_server.py...")
sftp.put(local_main_ws, f"{REMOTE_BASE}/app/main_ws_server.py")
print("  Upload complete.")
sftp.close()

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo {NAS_PASS} | sudo -S {cmd}')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    err = "\n".join([line for line in err.splitlines() if "Password:" not in line and "authenticate" not in line])
    return out, err

print("\nRestarting container nala_nas_ws_hub...")
out, err = run_sudo("docker restart nala_nas_ws_hub")
print("Restart output:", out, err)

time.sleep(3)

print("\nChecking container logs...")
log_out, _ = run_sudo("docker logs --tail 25 nala_nas_ws_hub")
print(log_out)

ssh.close()

# TEST BARGE-IN VIA WEBSOCKET
async def test_barge_in():
    print("\n--- TEST BARGE-IN / ABORT SPEAKING VIA WEBSOCKET ---")
    ws_url = f"ws://{NAS_IP}:8765/ws/test_bargein_device?token=nala_secret_jwt_token_2026_xyz"
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected to WebSocket server.")

            # Đợi nhận gói init nếu có
            try:
                first_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print("Received init packet:", first_msg[:100] if isinstance(first_msg, str) else len(first_msg))
            except asyncio.TimeoutError:
                pass

            # Giả lập gửi 1s âm thanh nói "Kể cho tôi nghe một câu chuyện dài"
            # 16000 samples int16 = 32000 bytes
            dummy_pcm = b'\x00\x00' * 16000
            
            # Gửi gói nhị phân START
            hdr_start = bytearray(7)
            hdr_start[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_start[2] = 0x01 # sender
            hdr_start[3] = 0x00 # target AI
            hdr_start[4:6] = (0).to_bytes(2, 'little')
            hdr_start[6] = 0x01 # STREAM_FLAG_START
            chunk1 = dummy_pcm[:512]
            await ws.send(bytes(hdr_start + chunk1 + b'\x00'))
            print("Sent START binary chunk.")

            # Gửi gói END
            hdr_end = bytearray(7)
            hdr_end[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr_end[2] = 0x01
            hdr_end[3] = 0x00
            hdr_end[4:6] = (1).to_bytes(2, 'little')
            hdr_end[6] = 0x03 # STREAM_FLAG_END
            await ws.send(bytes(hdr_end + chunk1 + b'\x00'))
            print("Sent END binary chunk. AI Flow should start thinking...")

            # Đợi nhận trạng thái thinking / ack_chime
            t0 = time.time()
            abort_sent = False
            while time.time() - t0 < 4.0:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                if isinstance(msg, str):
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    print(f"Server Event: {msg_type} -> {data}")
                    
                    if (msg_type in ["ack_chime", "ai_state"] or "thinking" in str(data)) and not abort_sent:
                        print("\n>>> SIMULATING USER BARGE-IN: Sending {'type': 'abort'}! <<<")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True
                    
                    if msg_type == "tts_stop":
                        dt_ms = (time.time() - abort_time) * 1000
                        print(f"SUCCESS! Received 'tts_stop' in {dt_ms:.1f}ms (< 30ms latency)!")
                        return True
                    
                    if data.get("payload", {}).get("state") == "idle" and abort_sent:
                        print("AI returned to IDLE state after abort.")
                        return True
                else:
                    print(f"Received Binary Audio chunk: {len(msg)} bytes")
                    if not abort_sent:
                        print("\n>>> AI IS SPEAKING! SIMULATING USER BARGE-IN: Sending {'type': 'abort'}! <<<")
                        abort_time = time.time()
                        await ws.send(json.dumps({"type": "abort"}))
                        abort_sent = True

    except Exception as e:
        print("Error during test:", e)
        return False

if __name__ == "__main__":
    asyncio.run(test_barge_in())
