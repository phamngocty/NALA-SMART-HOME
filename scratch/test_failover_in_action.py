import requests
import json
import time
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

NAS_URL = "http://192.168.1.114:8765"

print("--- Testing Auto-Failover when asking with invalid provider preference ---")
# Request with provider="non_existent_provider" or a failing provider
payload = {
    "message": "Bật máy lạnh phòng khách 25 độ",
    "provider": "custom"  # custom has no working url, so it should auto-failover to Groq/Gemini/DeepSeek!
}

t0 = time.time()
r = requests.post(f"{NAS_URL}/api/ai/chat", json=payload, timeout=15)
elapsed = time.time() - t0
print(f"Status: {r.status_code} in {elapsed:.2f}s")
if r.status_code == 200:
    data = r.json()
    print(f"Reply: '{data.get('reply')}'")
else:
    print(f"Error: {r.text}")

print("\n--- Checking Container Logs to verify Failover Trace ---")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')
stdin, stdout, stderr = ssh.exec_command('echo 271000 | sudo -S docker logs --tail 20 nala_nas_ws_hub')
logs = stdout.read().decode('utf-8', errors='replace')
for line in logs.splitlines():
    if any(k in line for k in ["Candidate", "Auto-falling back", "Attempting", "Processing intent with", "Local rule", "offline"]):
        print("  ->", line)
ssh.close()
