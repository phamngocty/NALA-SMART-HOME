import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts

reply = "Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh, kích hoạt kịch bản như \\"xem phim\\" hay \\"đi ngủ\\", và tắt hết thiết bị khi bạn ra khỏi nhà. Cứ ra lệnh tự nhiên nhé!"

# Let test chunks or character by character
parts = [
    "Mình là Nala, quản gia AI của nhà bạn đây!",
    "Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh",
    "kích hoạt kịch bản như \\"xem phim\\" hay \\"đi ngủ\\"",
    "và tắt hết thiết bị khi bạn ra khỏi nhà. Cứ ra lệnh tự nhiên nhé!",
    reply.replace("\\"", ""),
    reply.replace("/", " "),
    reply.replace("\\"", "").replace("/", " ")
]

async def test():
    for p in parts:
        try:
            comm = edge_tts.Communicate(p, "vi-VN-HoaiMyNeural")
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            print(f"PASS ({len(buf)} bytes): {p[:40]}")
        except Exception as e:
            print(f"FAIL ({e}): {p[:40]}")

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
