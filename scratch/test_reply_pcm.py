import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
from app.stt_tts_pipeline import AudioPipeline

pipe = AudioPipeline(stt_url="http://localhost:8095/v1/audio/transcriptions")
reply = "Mình là Nala, quản gia AI của nhà bạn đây! Mình có thể bật/tắt đèn, quạt, điều chỉnh máy lạnh, kích hoạt kịch bản như \\"xem phim\\" hay \\"đi ngủ\\", và tắt hết thiết bị khi bạn ra khỏi nhà. Cứ ra lệnh tự nhiên nhé!"

async def run():
    print("Testing text_to_pcm with reply...")
    pcm = await pipe.text_to_pcm(reply, voice="vi-VN-HoaiMyNeural")
    print("Result pcm length:", len(pcm))

asyncio.run(run())
'"""

stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
print("OUT:\n", stdout.read().decode('utf-8'))
print("ERR:\n", stderr.read().decode('utf-8'))
ssh.close()
