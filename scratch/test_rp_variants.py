import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def test(rate, pitch):
    try:
        comm = edge_tts.Communicate('Xin chao', 'vi-VN-HoaiMyNeural', rate=rate, pitch=pitch)
        await comm.save('/tmp/test_rp.mp3')
        print(f'rate={rate}, pitch={pitch}: SUCCESS')
    except Exception as e:
        print(f'rate={rate}, pitch={pitch}: FAIL -> {e}')

async def main():
    await test('+10%', '+0Hz')
    await test('-10%', '+0Hz')
    await test('+0%', '+5Hz')
    await test('+0%', '+50Hz')
    await test('+0%', '-50Hz')
    await test('+10%', '+10Hz')

asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print(stderr.read().decode())
ssh.close()
