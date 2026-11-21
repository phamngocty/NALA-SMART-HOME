import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def main():
    comm = edge_tts.Communicate('Xin chào Nala, tôi là trợ lý ảo!', 'vi-VN-HoaiMyNeural', rate='+10%', pitch='+5Hz')
    await comm.save('/tmp/test_edge.mp3')
    print('SUCCESS')
asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print("OUT:", stdout.read().decode())
print("ERR:", stderr.read().decode())
ssh.close()
