import paramiko
import sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio
from app.extension_mcp_service import ExtensionMCPService
async def t():
    s = ExtensionMCPService()
    print("Testing inside container:")
    res = await s.web_search("Hà Nội")
    print("Result:", res)
asyncio.run(t())
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
