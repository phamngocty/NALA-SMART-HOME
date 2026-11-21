import paramiko
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Connecting to NAS 192.168.1.114...")
ssh.connect('192.168.1.114', username='nas152', password='271000')

sftp = ssh.open_sftp()
remote_base = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app'

files_to_upload = [
    ('server_nas_hub/app/voiceprint_manager.py', f'{remote_base}/voiceprint_manager.py'),
    ('server_nas_hub/app/extension_mcp_service.py', f'{remote_base}/extension_mcp_service.py'),
    ('server_nas_hub/app/stt_tts_pipeline.py', f'{remote_base}/stt_tts_pipeline.py'),
    ('server_nas_hub/app/ai_agent_router.py', f'{remote_base}/ai_agent_router.py'),
    ('server_nas_hub/app/main_ws_server.py', f'{remote_base}/main_ws_server.py'),
    ('server_nas_hub/app/static/index.html', f'{remote_base}/static/index.html'),
]

for local_path, remote_path in files_to_upload:
    size = os.path.getsize(local_path)
    print(f"Uploading {local_path} ({size} bytes) -> {remote_path}...")
    sftp.put(local_path, remote_path)

sftp.close()

print("Restarting docker container nala_nas_ws_hub...")
stdin, stdout, stderr = ssh.exec_command("docker restart nala_nas_ws_hub")
print("Restart output:", stdout.read().decode())
err = stderr.read().decode()
if err:
    print("Restart error:", err)

ssh.close()
print("✅ Upload and restart completed successfully!")
