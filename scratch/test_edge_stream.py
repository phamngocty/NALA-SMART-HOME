import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def main():
    text = 'Xin chào! Mình là Nala, trợ lý ảo nhà thông minh của bạn.'
    voice = 'vi-VN-HoaiMyNeural'
    rate = '+0%'
    pitch = '+0Hz'
    try:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        buf = bytearray()
        async for chunk in comm.stream():
            if chunk['type'] == 'audio':
                buf.extend(chunk['data'])
        print('STREAM OK, len:', len(buf))
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
