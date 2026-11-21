import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import edge_tts, asyncio
async def main():
    voices = await edge_tts.list_voices()
    for v in voices:
        if 'vi-VN' in v['ShortName'] or 'vi' in v['Locale'].lower():
            print(v['ShortName'], v['Gender'], v['FriendlyName'])
asyncio.run(main())
" """

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
