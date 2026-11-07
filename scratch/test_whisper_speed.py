import urllib.request
import json
import io
import wave
import time

sample_rate = 16000
duration = 1.0
wav_io = io.BytesIO()
with wave.open(wav_io, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(b'\x00' * int(sample_rate * duration * 2))

wav_bytes = wav_io.getvalue()
boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
parts = []
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="audio.wav"\r\nContent-Type: audio/wav\r\n\r\n'.encode('utf-8'))
parts.append(wav_bytes)
parts.append(f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nSystran/faster-whisper-small\r\n'.encode('utf-8'))
parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="language"\r\n\r\nvi\r\n'.encode('utf-8'))
parts.append(f'--{boundary}--\r\n'.encode('utf-8'))
body = b''.join(parts)

req = urllib.request.Request(
    'http://192.168.1.114:8095/v1/audio/transcriptions',
    data=body,
    headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
)

t0 = time.time()
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        res = json.loads(resp.read().decode())
        dt = (time.time() - t0) * 1000
        print(f'Whisper response in {dt:.1f}ms: {res}')
except Exception as e:
    print('Error:', e)
