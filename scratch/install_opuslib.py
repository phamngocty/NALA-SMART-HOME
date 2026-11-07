import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'echo 271000 | sudo -S docker exec nala_nas_ws_hub pip install opuslib'
_, out, err = ssh.exec_command(cmd)
print("Pip install:", out.read().decode('utf-8', errors='replace').strip())

cmd2 = 'echo 271000 | sudo -S docker exec nala_nas_ws_hub python -c "import opuslib; print(\'OpusLib imported successfully!\')"'
_, out2, err2 = ssh.exec_command(cmd2)
print("Test import:", out2.read().decode('utf-8', errors='replace').strip(), err2.read().decode('utf-8', errors='replace').strip())

ssh.close()
