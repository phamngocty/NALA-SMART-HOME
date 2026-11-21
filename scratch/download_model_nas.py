import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

commands = [
    "mkdir -p /home/nas152/nala-voice-intercom-system/server_nas_hub/app/models",
    "mkdir -p /home/nas152/nala-voice-intercom-system/server_nas_hub/app/data/voiceprints",
    "cd /home/nas152/nala-voice-intercom-system/server_nas_hub/app/models && wget -q -c https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx -O campplus_model.onnx",
    "ls -lh /home/nas152/nala-voice-intercom-system/server_nas_hub/app/models/campplus_model.onnx"
]

for cmd in commands:
    print(f"Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out: print("OUT:", out)
    if err: print("ERR:", err)

ssh.close()
print("Done!")
