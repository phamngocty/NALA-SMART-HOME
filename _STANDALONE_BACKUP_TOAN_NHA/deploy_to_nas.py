import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

NAS_IP = "192.168.1.114"
NAS_USER = "nas152"
NAS_PASS = "271000"
REMOTE_BASE = "/home/nas152/nala-voice-intercom-system/server_nas_hub/app"
LOCAL_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server_nas_hub", "app")

print(f"Connecting to NAS {NAS_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NAS_IP, username=NAS_USER, password=NAS_PASS, timeout=10)

sftp = ssh.open_sftp()

# Files to update
files = [
    ("ha_bridge.py", os.path.join(LOCAL_BASE, "ha_bridge.py"), f"{REMOTE_BASE}/ha_bridge.py"),
    ("intercom_router.py", os.path.join(LOCAL_BASE, "intercom_router.py"), f"{REMOTE_BASE}/intercom_router.py"),
    ("ai_agent_router.py", os.path.join(LOCAL_BASE, "ai_agent_router.py"), f"{REMOTE_BASE}/ai_agent_router.py"),
    ("ai_config.json", os.path.join(LOCAL_BASE, "ai_config.json"), f"{REMOTE_BASE}/ai_config.json"),
    ("all_house_config.json", os.path.join(LOCAL_BASE, "all_house_config.json"), f"{REMOTE_BASE}/all_house_config.json"),
    ("devices.json", os.path.join(LOCAL_BASE, "devices.json"), f"{REMOTE_BASE}/devices.json"),
    ("main_ws_server.py", os.path.join(LOCAL_BASE, "main_ws_server.py"), f"{REMOTE_BASE}/main_ws_server.py"),
    ("static/index.html", os.path.join(LOCAL_BASE, "static", "index.html"), f"{REMOTE_BASE}/static/index.html"),
]

for name, local_p, remote_p in files:
    print(f"Uploading {name} -> {remote_p}...")
    sftp.put(local_p, remote_p)
    print(f"✓ Uploaded {name}")

sftp.close()

print("Restarting docker container nala_nas_ws_hub...")
stdin, stdout, stderr = ssh.exec_command("docker restart nala_nas_ws_hub")
print("Output:", stdout.read().decode('utf-8').strip())

stdin, stdout, stderr = ssh.exec_command("docker ps --filter name=nala_nas_ws_hub")
print("Container status:\n", stdout.read().decode('utf-8'))

ssh.close()
print("Deploy to NAS complete!")
