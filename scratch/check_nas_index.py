import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = """python3 -c "
with open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/static/index.html') as f:
    text = f.read()
idx = text.find('async function fetchModelsForProvider')
print(text[idx:idx+1500])
" """

_, out, err = ssh.exec_command(cmd)
print(out.read().decode())
ssh.close()
