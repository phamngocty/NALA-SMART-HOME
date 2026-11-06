import sys
import os
import paramiko
import time
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_USER = 'nas152'
NAS_PASS = '271000'
REMOTE_BASE = '/home/nas152/nala-voice-intercom-system/server_nas_hub'

local_router = os.path.abspath('server_nas_hub/app/ai_agent_router.py')
local_html = os.path.abspath('server_nas_hub/app/static/index.html')
local_stt_tts = os.path.abspath('server_nas_hub/app/stt_tts_pipeline.py')

print(f"Connecting to NAS {NAS_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username=NAS_USER, password=NAS_PASS)

sftp = ssh.open_sftp()

def upload(local_p, remote_p):
    print(f"Uploading {os.path.basename(local_p)} -> {remote_p}...")
    sftp.put(local_p, remote_p)
    print("  Done.")

upload(local_router, f"{REMOTE_BASE}/app/ai_agent_router.py")
upload(local_html, f"{REMOTE_BASE}/app/static/index.html")
upload(local_stt_tts, f"{REMOTE_BASE}/app/stt_tts_pipeline.py")

sftp.close()

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo {NAS_PASS} | sudo -S {cmd}')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    err = "\n".join([line for line in err.splitlines() if "Password:" not in line and "authenticate" not in line])
    return out, err

print("\nRestarting container nala_nas_ws_hub...")
out, err = run_sudo("docker restart nala_nas_ws_hub")
print("Restart output:", out, err)

time.sleep(4)

print("\nChecking container logs...")
out, err = run_sudo("docker logs --tail 25 nala_nas_ws_hub")
print("Logs:\n", out)

ssh.close()

# Test API config from NAS
print("\n--- Testing Live API on NAS ---")
try:
    resp = requests.get(f"http://{NAS_IP}:8765/api/ai/config", timeout=5)
    print("GET /api/ai/config status:", resp.status_code)
    cfg = resp.json()
    print("Active Provider:", cfg.get("active_provider"))
    print("Auto Fallback:", cfg.get("auto_fallback"))
    print("STT Provider:", cfg.get("stt_provider"))
    print("Gemini Model:", cfg.get("gemini", {}).get("model"))
    print("Groq Model:", cfg.get("groq", {}).get("model"))
    print("DeepSeek Model:", cfg.get("deepseek", {}).get("model"))
except Exception as ex:
    print("API test failed:", ex)
