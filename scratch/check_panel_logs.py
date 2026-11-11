import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)
stdin, stdout, stderr = ssh.exec_command("docker logs --tail 400 nala_nas_ws_hub 2>&1")
output = stdout.read().decode('utf-8', errors='replace')
lines = output.splitlines()
for line in lines:
    if "23:3" in line or "23:4" in line:
        if any(k in line for k in ["WebSocket", "Client:", "connect", "disconnect", "OTA"]):
            print(line)
ssh.close()
