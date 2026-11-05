import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)

cmd = "python3 -c \"import os, glob, datetime, json; fw_dir = '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/firmware'; files = glob.glob(os.path.join(fw_dir, '*.bin')); out = [{'name': os.path.basename(f), 'size_mb': round(os.path.getsize(f)/(1024*1024), 2), 'mtime': datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M:%S')} for f in files if os.path.basename(f) != 'firmware_latest.bin']; out.sort(key=lambda x: x['mtime']); print(json.dumps([x for x in out if '20261031' in x['name'] or '20261104' in x['name']]))\""

stdin, stdout, stderr = ssh.exec_command(cmd)
raw = stdout.read().decode('utf-8')
data = json.loads(raw)
ssh.close()

print(f"Total builds on Oct 31 & Nov 04: {len(data)}")
for item in data:
    print(f"{item['mtime']} | {item['size_mb']} MB | {item['name']}")
