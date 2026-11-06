import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

def run_cmd(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    return out

print("=== LS DATA ===")
print(run_cmd("ls -la /home/nas152/nala-voice-intercom-system/server_nas_hub/data"))

print("\n=== AI CONFIG (if exists) ===")
print(run_cmd("cat /home/nas152/nala-voice-intercom-system/server_nas_hub/data/ai_agent_config.json"))

print("\n=== ENV FILE ===")
print(run_cmd("cat /home/nas152/nala-voice-intercom-system/server_nas_hub/.env"))

ssh.close()
