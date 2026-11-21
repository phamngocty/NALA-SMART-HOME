import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'docker exec nala_nas_ws_hub python3 -c "from app.main_ws_server import ai_router; print(\'config_file:\', ai_router.config_file); print(\'gemini key len:\', len(ai_router.config.get(\'gemini\', {}).get(\'api_key\', \'\'))); print(\'safe config:\', ai_router.get_safe_config())"'
stdin, stdout, stderr = ssh.exec_command(cmd)
print("STDOUT:\n", stdout.read().decode())
print("STDERR:\n", stderr.read().decode())

ssh.close()
