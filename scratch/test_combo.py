import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def test(txt, r, p):
    try:
        c = edge_tts.Communicate(txt, 'vi-VN-HoaiMyNeural', rate=r, pitch=p)
        b = bytearray()
        async for chunk in c.stream():
            if chunk['type'] == 'audio': b.extend(chunk['data'])
        print(f'{r}, {p}: OK ({len(b)} bytes)')
    except Exception as e:
        print(f'{r}, {p}: ERR ({e})')

async def main():
    txt = 'Xin chào, tôi là Nala'
    for r in ['-20%', '-10%', '+0%', '+10%', '+20%']:
        for p in ['-10Hz', '+0Hz', '+10Hz']:
            await test(txt, r, p)
asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
