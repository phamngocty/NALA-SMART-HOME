import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """docker exec nala_nas_ws_hub python3 -c '
import os
try:
    import sherpa_onnx
    print("sherpa_onnx is installed: YES")
except ImportError as e:
    print("sherpa_onnx is installed: NO -", e)

from app.voiceprint_manager import VoiceprintManager
vm = VoiceprintManager()
print("VoiceprintManager is_ready:", vm.is_ready)
print("Storage dir:", vm.storage_dir)
print("Model path:", vm.model_path)
print("Speakers:", vm.list_speakers())
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
