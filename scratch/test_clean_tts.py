import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts
import re

text = "Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh, kích hoạt kịch bản như \\"xem phim\\" hay \\"đi ngủ\\", và tắt hết thiết bị khi bạn ra khỏi nhà. Cứ ra lệnh tự nhiên nhé!"

clean = re.sub(r"[\\\"*`#_{}\\[\\]<>/]", " ", text).strip()
clean = re.sub(r"\\s+", " ", clean)

print("Cleaned text:", clean)

async def test():
    comm = edge_tts.Communicate(clean, "vi-VN-HoaiMyNeural")
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    print("SUCCESS! Received", len(buf), "bytes audio!")

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
