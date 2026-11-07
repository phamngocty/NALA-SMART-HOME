import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'docker exec nala_nas_ws_hub python -c "import openwakeword; from openwakeword.model import Model; m = Model(); print(\'MODELS:\', list(m.models.keys()))"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
print('ERR:', stderr.read().decode())
ssh.close()
