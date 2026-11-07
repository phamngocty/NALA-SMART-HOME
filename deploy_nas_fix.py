import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to NAS 192.168.1.114...")
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=10)
    
    sftp = ssh.open_sftp()
    for fname in ["main_ws_server.py", "wake_word_manager.py"]:
        local_file = f"server_nas_hub/app/{fname}"
        remote_file = f"/home/nas152/nala-voice-intercom-system/server_nas_hub/app/{fname}"
        print(f"Uploading {local_file} -> {remote_file}...")
        sftp.put(local_file, remote_file)
    sftp.close()
    print("Upload complete!")

    print("Restarting docker container nala_nas_ws_hub...")
    stdin, stdout, stderr = ssh.exec_command("docker restart nala_nas_ws_hub")
    print("Output:", stdout.read().decode('utf-8'))
    err = stderr.read().decode('utf-8')
    if err:
        print("Error:", err)
    
    print("Waiting 4s for container to start up...")
    time.sleep(4)

    stdin, stdout, stderr = ssh.exec_command("docker logs --tail 30 nala_nas_ws_hub")
    print("Container startup logs:")
    print(stdout.read().decode('utf-8', errors='replace'))

    ssh.close()
    print("Deployment finished successfully!")

except Exception as e:
    print("Deployment failed:", e)
    sys.exit(1)
