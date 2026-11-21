import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)

test_script = """
import os
import wave
import numpy as np
from voiceprint_manager import voiceprintManager

rec_dir = "/app/app/recordings"
files = [f for f in os.listdir(rec_dir) if f.endswith(".wav")]
print(f"Total recordings found: {len(files)}")
for f in files[:5]:
    fp = os.path.join(rec_dir, f)
    with wave.open(fp, 'rb') as w:
        print(f"- {f}: {w.getnchannels()}ch, {w.getframerate()}Hz, {w.getnframes()/w.getframerate():.2f}s")

if len(files) >= 2:
    f1 = os.path.join(rec_dir, files[0])
    f2 = os.path.join(rec_dir, files[1])
    
    with wave.open(f1, 'rb') as w:
        pcm1 = w.readframes(w.getnframes())
    with wave.open(f2, 'rb') as w:
        pcm2 = w.readframes(w.getnframes())
        
    print(f"Testing enrollment with {files[0]} as 'User_1'...")
    ok, msg = voiceprintManager.enroll("User_1", pcm1)
    print("Enroll result:", ok, msg)
    
    # Identify with same file (f1)
    spk, score, scores = voiceprintManager.identify(pcm1, threshold=0.50)
    print(f"Identify with f1 (Same audio): Match='{spk}', Score={score:.3f}, All={scores}")
    
    # Identify with f2
    spk2, score2, scores2 = voiceprintManager.identify(pcm2, threshold=0.50)
    print(f"Identify with f2: Match='{spk2}', Score={score2:.3f}, All={scores2}")
    
    voiceprintManager.delete("User_1")
"""

sftp = ssh.open_sftp()
sftp.put('server_nas_hub/app/voiceprint_manager.py', '/home/nas152/nala-voice-intercom-system/server_nas_hub/app/voiceprint_manager.py')
with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/test_real.py', 'w') as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('docker exec nala_nas_ws_hub python3 /app/app/test_real.py')
print("STDOUT:\n" + stdout.read().decode())
err = stderr.read().decode()
if err: print("STDERR:\n" + err)

ssh.close()
