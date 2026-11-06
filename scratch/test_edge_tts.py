import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
import edge_tts

text = "Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật tắt đèn, quạt, điều chỉnh máy lạnh."
voice = "vi-VN-HoaiMyNeural"

async def test():
    print(f"Testing voice {voice}...")
    try:
        comm = edge_tts.Communicate(text, voice)
        mp3_buf = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                mp3_buf.extend(chunk["data"])
        print(f"Success! Received {len(mp3_buf)} bytes mp3.")
    except Exception as e:
        print(f"Failed with voice {voice}:", type(e), e)

    # List available Vietnamese voices
    try:
        voices = await edge_tts.list_voices()
        vn_voices = [v for v in voices if "vi-VN" in v["Locale"]]
        print("Available Vietnamese voices:")
        for v in vn_voices:
            print(" -", v["ShortName"], v["Gender"])
    except Exception as e:
        print("List voices failed:", e)

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
