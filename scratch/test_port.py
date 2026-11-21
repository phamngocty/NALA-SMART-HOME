import paramiko
import json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

stdin, stdout, stderr = ssh.exec_command('docker inspect nala_nas_ws_hub')
info = json.loads(stdout.read().decode())[0]
print("NetworkMode:", info["HostConfig"]["NetworkMode"])
print("PortBindings:", info["HostConfig"]["PortBindings"])
print("Cmd:", info["Config"]["Cmd"])
print("Env:", [e for e in info["Config"]["Env"] if "PORT" in e or "WS" in e])

# Also check netstat inside container or on host
stdin, stdout, stderr = ssh.exec_command('netstat -tlpn | grep python')
print("Listening ports:\n", stdout.read().decode())

ssh.close()
