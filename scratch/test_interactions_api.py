import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """python3 -c '
import urllib.request
import json
import time

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
url = "https://generativelanguage.googleapis.com/v1beta/interactions"
payload = {
    "model": "gemini-3.8-flash",
    "input": "Trả lời ngắn gọn 1 từ: OK"
}
data = json.dumps(payload).encode("utf-8")
headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": key
}
req = urllib.request.Request(url, data=data, headers=headers)
t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=15) as res:
        print("INTERACTIONS API SUCCESS (" + str(round(time.time()-t0, 2)) + "s):")
        print(res.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print(f"INTERACTIONS API HTTP {e.code}:", e.read().decode("utf-8"))
except Exception as e:
    print("Error:", e)
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
ssh.close()
