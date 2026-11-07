import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'echo 271000 | sudo -S docker exec nala_nas_ws_hub which ffmpeg'
_, out, err = ssh.exec_command(cmd)
print("FFMPEG:", out.read().decode('utf-8', errors='replace').strip())

cmd2 = 'echo 271000 | sudo -S docker exec nala_nas_ws_hub find /usr -name "*opus*.so*" 2>/dev/null'
_, out2, _ = ssh.exec_command(cmd2)
print("OPUS LIB:", out2.read().decode('utf-8', errors='replace').strip())

ssh.close()
