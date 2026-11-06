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

for m in ["gemini-3.8-pro", "gemini-2.5-pro", "gemini-flash-latest", "gemini-pro-latest", "gemini-3.8-flash"]:
    payload = {
        "model": m,
        "input": "Reply OK"
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": key
    }
    req = urllib.request.Request(url, data=data, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=12) as res:
            body = res.read().decode("utf-8")
            print(f"[{m}] SUCCESS ({round(time.time()-t0, 2)}s):", body[:120])
            break
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8")
        print(f"[{m}] HTTP {e.code} ({round(time.time()-t0, 2)}s):", err[:100])
    except Exception as e:
        print(f"[{m}] Err ({round(time.time()-t0, 2)}s):", e)
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))
ssh.close()
