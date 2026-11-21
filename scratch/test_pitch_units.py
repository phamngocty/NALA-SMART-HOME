import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def test(p):
    try:
        c = edge_tts.Communicate('Xin chao', 'vi-VN-HoaiMyNeural', pitch=p)
        b = bytearray()
        async for chunk in c.stream():
            if chunk['type'] == 'audio': b.extend(chunk['data'])
        print(f'{p}: OK ({len(b)} bytes)')
    except Exception as e:
        print(f'{p}: ERR ({e})')

async def main():
    for p in ['+0Hz', '+2Hz', '+5Hz', '+10Hz', '+20Hz', '-5Hz', '-10Hz', '+5st', '+10st', '-5st', '+5%', '+10%', '-5%']:
        await test(p)
asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
