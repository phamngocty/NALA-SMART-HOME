import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('192.168.1.114', username='nas152', password='271000')

remote_script = """
import json

path = '/home/nas152/nala-voice-intercom-system/server_nas_hub/data/wake_config.json'
try:
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
except Exception:
    cfg = {}

cfg['selected_model'] = 'hey_nala'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)

print('SUCCESS: Updated wake_config.json to hey_nala')
"""

sftp = s.open_sftp()
with sftp.file('/tmp/update_wake_cfg.py', 'w') as f:
    f.write(remote_script)
sftp.close()

_, out, err = s.exec_command('echo 271000 | sudo -S python3 /tmp/update_wake_cfg.py')
print(out.read().decode('utf-8', errors='ignore'))
print(err.read().decode('utf-8', errors='ignore'))
s.close()
