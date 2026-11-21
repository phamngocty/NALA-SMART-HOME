import paramiko
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

print("Installing sherpa-onnx in Docker container nala_nas_ws_hub...")
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub pip install sherpa-onnx')
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())

print("Testing sherpa-onnx import...")
stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python3 -c "import sherpa_onnx; print(\'sherpa-onnx version:\', sherpa_onnx.__version__)"')
print("Import test:", stdout.read().decode().strip())

ssh.close()
