import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
print("Connecting to NAS Hub SSH to monitor Wake Word events in real time...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)
    # Stream docker logs filtered for wake word and audio events
    stdin, stdout, stderr = ssh.exec_command("docker logs -f --tail 20 nala_nas_ws_hub")
    
    start_time = time.time()
    # Read for up to 30 seconds
    while time.time() - start_time < 30:
        line = stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        line_str = line.strip()
        # Filter for interesting logs
        if any(kw in line_str.lower() for kw in ["wake", "oww", "score", "vad", "target=5", "channel=5", "mochi", "intercom", "detected"]):
            print(f"[WAKE-LOG] {line_str}")
        elif "audio" in line_str.lower() or "ai" in line_str.lower():
            print(f"[AUDIO-LOG] {line_str}")
    ssh.close()
    print("Monitoring finished.")
except Exception as e:
    print(f"Error: {e}")
