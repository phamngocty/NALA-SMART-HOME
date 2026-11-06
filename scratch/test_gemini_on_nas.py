import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """python3 -c '
import urllib.request
import json
import time

key = "AQ.Ab8RN6Knoug0OVEzQ_b6u7qOvVs-tsDFrD4LA_LLkNYCYq-Vgw"
for m in ["gemini-3.8-flash", "gemini-flash-latest", "gemini-2.5-flash"]:
    t0 = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={key}"
    data = json.dumps({"contents": [{"parts": [{"text": "Hello"}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            body = res.read().decode("utf-8")
            print(f"[{m}] SUCCESS ({round(time.time()-t0, 2)}s):", body[:150])
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"[{m}] HTTP {e.code} ({round(time.time()-t0, 2)}s):", err_body[:150])
    except Exception as e:
        print(f"[{m}] Error ({round(time.time()-t0, 2)}s):", e)
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("=== NAS TEST OUTPUT ===")
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
ssh.close()
