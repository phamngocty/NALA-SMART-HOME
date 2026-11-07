import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)

cmd = """docker exec nala_nas_ws_hub python -c "
import openwakeword
from openwakeword.model import Model
import os

print('OpenWakeWord models dir:', getattr(openwakeword, 'MODELS_DIR', None))
# Try initializing Model
try:
    m = Model(wakeword_models=['hey_jarvis', 'alexa'])
    print('Loaded model keys:', list(m.models.keys()))
except Exception as e:
    print('Failed:', e)
"
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))
ssh.close()
