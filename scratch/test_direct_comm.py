import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts
import traceback

text = "Chào bạn! Mình là Nala, quản gia AI của nhà bạn đây. Cần bật tắt gì cứ nói nhé!"
voice = "vi-VN-HoaiMyNeural"

async def test():
    try:
        comm = edge_tts.Communicate(text, voice)
        mp3 = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                mp3.extend(chunk["data"])
        print("Success! Got", len(mp3), "bytes mp3.")
    except Exception as e:
        print("Failed:", type(e), e)
        traceback.print_exc()

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
