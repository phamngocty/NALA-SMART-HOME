import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

for p in [
    "/home/nas152/nala-voice-intercom-system/server_nas_hub/app/ai_config.json",
    "/home/nas152/nala-voice-intercom-system/server_nas_hub/data/ai_config.json"
]:
    stdin, stdout, stderr = ssh.exec_command(f"cat {p}")
    content = stdout.read().decode()
    print(f"=== {p} ===")
    try:
        cfg = json.loads(content)
        for k, v in cfg.items():
            if isinstance(v, dict) and "api_key" in v:
                ak = v.get("api_key", "")
                print(f"  {k}: model={v.get('model')}, api_key={ak[:6]}...{ak[-4:] if len(ak)>10 else ''}")
            else:
                print(f"  {k}: {v}")
    except Exception as e:
        print("  Error:", e, content[:200])

ssh.close()
