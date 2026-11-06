import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts

text = "Chào bạn! Mình là Nala, quản gia AI của nhà bạn đây. Cần bật tắt gì cứ nói nhé!"

async def try_voice(v, t):
    try:
        c = edge_tts.Communicate(t, v)
        b = bytearray()
        async for chunk in c.stream():
            if chunk["type"] == "audio":
                b.extend(chunk["data"])
        print(f"[{v}] SUCCESS: {len(b)} bytes")
        return True
    except Exception as e:
        print(f"[{v}] FAIL: {e}")
        return False

async def main():
    for v in ["vi-VN-NamMinhNeural", "vi-VN-HoaiMyNeural", "en-US-JennyNeural"]:
        await try_voice(v, text)
        await try_voice(v, "Xin chào")

asyncio.run(main())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
