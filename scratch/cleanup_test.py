import paramiko

s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python -c "
import json
path = '/app/data/devices.json'
with open(path) as f:
    d = json.load(f)
if 'TEST99' in d:
    del d['TEST99']
    with open(path, 'w') as f:
        json.dump(d, f, indent=2)
    print('Cleaned TEST99')
else:
    print('Already clean')
" """

_, out, err = s.exec_command(cmd)
print(out.read().decode())
s.close()
