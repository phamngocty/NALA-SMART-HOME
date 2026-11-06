import sys
import os
import paramiko
import time
import httpx

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = '192.168.1.114'
NAS_USER = 'nas152'
NAS_PASS = '271000'
REMOTE_BASE = '/home/nas152/nala-voice-intercom-system/server_nas_hub'

files_to_sync = [
    ('server_nas_hub/app/ai_agent_router.py', f'{REMOTE_BASE}/app/ai_agent_router.py'),
    ('server_nas_hub/app/main_ws_server.py', f'{REMOTE_BASE}/app/main_ws_server.py'),
    ('server_nas_hub/app/stt_tts_pipeline.py', f'{REMOTE_BASE}/app/stt_tts_pipeline.py'),
    ('server_nas_hub/app/static/index.html', f'{REMOTE_BASE}/app/static/index.html'),
]

print(f"Connecting to NAS {NAS_IP} via SSH...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username=NAS_USER, password=NAS_PASS)

sftp = ssh.open_sftp()
for local_rel, remote_abs in files_to_sync:
    local_abs = os.path.abspath(local_rel)
    print(f"Uploading {local_rel} -> {remote_abs}...")
    sftp.put(local_abs, remote_abs)
sftp.close()
print("All files uploaded successfully!")

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo {NAS_PASS} | sudo -S {cmd}')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    err = "\n".join([line for line in err.splitlines() if "Password:" not in line and "authenticate" not in line])
    return out, err

print("\nRestarting docker container nala_nas_ws_hub...")
out, err = run_sudo("docker restart nala_nas_ws_hub")
print("Restart output:", out, err)

print("Waiting 5s for server warmup...")
time.sleep(5)

out, err = run_sudo("docker logs --tail 30 nala_nas_ws_hub")
print("\nRecent container logs:\n", out)

ssh.close()
