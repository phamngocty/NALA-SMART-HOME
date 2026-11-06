import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts

tests = [
    "Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh",
    "Mình có thể bật hoặc tắt đèn, quạt, điều chỉnh máy lạnh",
    "kích hoạt kịch bản như \\"xem phim\\" hay \\"đi ngủ\\"",
    "kích hoạt kịch bản như xem phim hay đi ngủ",
]

async def test():
    for t in tests:
        try:
            comm = edge_tts.Communicate(t, "vi-VN-HoaiMyNeural")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            print(f"PASS ({len(buf)} bytes): {t}")
        except Exception as e:
            print(f"FAIL ({e}): {t}")

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
