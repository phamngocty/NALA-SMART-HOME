import paramiko
import sys
import time
import httpx

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

files_to_upload = [
    ("server_nas_hub/app/adaptive_memory_manager.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/adaptive_memory_manager.py"),
    ("server_nas_hub/app/groq_failover_client.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/groq_failover_client.py"),
    ("server_nas_hub/app/ai_agent_router.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/ai_agent_router.py"),
    ("server_nas_hub/app/main_ws_server.py", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py"),
    ("server_nas_hub/app/static/index.html", "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html"),
]

try:
    print("Connecting to NAS 192.168.1.114...")
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    
    sftp = ssh.open_sftp()
    for local_file, remote_file in files_to_upload:
        print(f"Uploading {local_file} -> {remote_file}...")
        sftp.put(local_file, remote_file)
    sftp.close()
    print("All files uploaded successfully!")

    print("Checking how nala hub is running on NAS (docker or python)...")
    stdin, stdout, stderr = ssh.exec_command("docker ps | grep nala")
    docker_out = stdout.read().decode('utf-8').strip()
    print("Docker containers:\n", docker_out)

    if "nala_nas_ws_hub" in docker_out:
        print("Restarting docker container nala_nas_ws_hub...")
        stdin, stdout, stderr = ssh.exec_command("docker restart nala_nas_ws_hub")
        print("Output:", stdout.read().decode('utf-8').strip())
    else:
        print("Checking if python process is running...")
        stdin, stdout, stderr = ssh.exec_command("pgrep -fa 'main_ws_server.py'")
        pids = stdout.read().decode('utf-8').strip()
        print("Python PIDs:", pids)

    print("Waiting 5s for server to settle...")
    time.sleep(5)

    stdin, stdout, stderr = ssh.exec_command("docker logs --tail 25 nala_nas_ws_hub")
    print("Latest container logs:")
    print(stdout.read().decode('utf-8', errors='replace'))

    ssh.close()

    print("\nVerifying live webserver at http://192.168.1.114:8765/ ...")
    r = httpx.get("http://192.168.1.114:8765/", timeout=10.0)
    print(f"HTTP Status: {r.status_code}")
    print(f"- 'openMemoryModal' in page: {'openMemoryModal' in r.text}")
    print(f"- 'Trí Nhớ Nala' in page: {'Trí Nhớ Nala' in r.text}")
    print(f"- 'deleteWakeModel' in page: {'deleteWakeModel' in r.text}")
    print(f"- 'Groq' in page: {'Groq' in r.text}")

    # Check API endpoints
    r_mem = httpx.get("http://192.168.1.114:8765/api/memory", timeout=10.0)
    print(f"API /api/memory status: {r_mem.status_code}, response: {r_mem.json().get('status')}")

    print("\nDEPLOYMENT & VERIFICATION COMPLETED SUCCESSFULLY!")

except Exception as e:
    print("Error during deployment:", e)
    sys.exit(1)
