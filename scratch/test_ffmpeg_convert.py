import paramiko
import numpy as np
import io, wave

# Make WAV bytes
t = np.linspace(0, 1.0, 16000, False)
sine = (np.sin(2 * np.pi * 440 * t) * 16384).astype(np.int16).tobytes()

wav_buf = io.BytesIO()
with wave.open(wav_buf, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(sine)
wav_bytes = wav_buf.getvalue()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

import base64
b64_wav = base64.b64encode(wav_bytes).decode('utf-8')

cmd = f"""docker exec nala_nas_ws_hub python3 -c '
import base64
from app.main_ws_server import convert_audio_to_pcm16k
wav = base64.b64decode("{b64_wav}")
pcm = convert_audio_to_pcm16k(wav)
print("Converted WAV to PCM length:", len(pcm) if pcm else 0)

# Also test raw PCM
pcm2 = convert_audio_to_pcm16k(pcm)
print("Converted raw PCM without header:", len(pcm2) if pcm2 else 0)
'"""

stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:", stdout.read().decode())
print("STDERR:", stderr.read().decode())
ssh.close()
