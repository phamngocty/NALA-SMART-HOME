import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000", timeout=5)

cmd = """docker exec nala_nas_ws_hub python -c "
import openwakeword
from openwakeword.model import Model
import numpy as np

m = Model(['hey_jarvis', 'alexa'])
print('Models loaded:', list(m.models.keys()))

# Feed 16 blocks of silence to test predict pipeline
for _ in range(16):
    dummy_audio = np.zeros(1280, dtype=np.int16)
    res = m.predict(dummy_audio)
print('Predict test on zeros succeeded! Sample output:', res)
"
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
print(stderr.read().decode('utf-8', errors='replace'))
ssh.close()
