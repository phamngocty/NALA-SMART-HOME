import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python3 --version')
print('Python version:', stdout.read().decode().strip())
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub pip list')
pip_list = stdout.read().decode()
found = [line for line in pip_list.splitlines() if any(k in line.lower() for k in ['sherpa', 'onnx', 'soundfile', 'scipy', 'numpy'])]
print('Found packages:', found)
ssh.close()
