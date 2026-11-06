import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("192.168.1.114", username="nas152", password="271000")

stdin, stdout, stderr = ssh.exec_command("find /home/nas152/ -name ota_meta.json -o -name '*.bin'")
print("Found files:\n", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command("docker exec nala_nas_ws_hub ls -la /app/firmware || ls -la /app")
print("Container files:\n", stdout.read().decode())

stdin, stdout, stderr = ssh.exec_command("docker logs --tail 50 nala_nas_ws_hub | grep -i ota")
print("OTA logs:\n", stdout.read().decode())

ssh.close()
