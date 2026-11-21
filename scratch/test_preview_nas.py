import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def main():
    comm = edge_tts.Communicate('Xin chào! Mình là Nala, trợ lý nhà thông minh của bạn.', 'vi-VN-HoaiMyNeural', rate='+10%', pitch='+15Hz')
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk['type'] == 'audio':
            buf.extend(chunk['data'])
    print(f'SUCCESS: {len(buf)} bytes')
asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
