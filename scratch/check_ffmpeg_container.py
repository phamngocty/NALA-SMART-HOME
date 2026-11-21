import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = "docker exec nala_nas_ws_hub which ffmpeg"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("which ffmpeg:", stdout.read().decode().strip())
err = stderr.read().decode().strip()
if err:
    print("stderr:", err)
ssh.close()
