import json
import httpx
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

# Read ai_agent_config.json on NAS
sftp = ssh.open_sftp()
with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/data/ai_agent_config.json', 'r') as f:
    cfg = json.load(f)
sftp.close()
ssh.close()

gemini_key = cfg.get('gemini', {}).get('api_key', '')
print("Gemini key prefix/suffix:", gemini_key[:8], "...", gemini_key[-4:])

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
r = httpx.get(url, timeout=15)
print("Status code:", r.status_code)
if r.status_code == 200:
    models = r.json().get('models', [])
    print(f"Total models available: {len(models)}")
    for m in models:
        name = m.get('name', '')
        methods = m.get('supportedGenerationMethods', [])
        if 'generateContent' in methods:
            print(f" - {name}")
else:
    print("Error response:", r.text[:500])
