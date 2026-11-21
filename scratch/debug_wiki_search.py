import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio, httpx, urllib.parse, json

async def test():
    q = "hồ gươm"
    url = f"https://vi.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(q)}&utf8=&format=json"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url, headers={"User-Agent": "NALA-Hub/3.2.0"})
        print("Wiki search status:", r.status_code)
        data = r.json()
        items = data.get("query", {}).get("search", [])
        if items:
            print("Found wiki item:", items[0].get("title"))
            print("Snippet:", items[0].get("snippet"))

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
