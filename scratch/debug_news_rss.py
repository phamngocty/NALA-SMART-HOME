import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import asyncio, httpx, urllib.parse, xml.etree.ElementTree as ET, re

async def test():
    q = "giá vàng hôm nay"
    # Google News RSS (completely free and unblocked real-time search)
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=vi&gl=VN&ceid=VN:vi"
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        print("RSS status:", r.status_code)
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            items = root.findall(".//item")
            print(f"Found {len(items)} news items:")
            for item in items[:3]:
                title = item.find("title").text if item.find("title") is not None else ""
                print(" -", title)

asyncio.run(test())
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
