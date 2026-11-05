import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)

cmd = "docker exec nala_nas_ws_hub cp /app/app/firmware/firmware_20261031_184746_firmware_v3.0.0.bin /app/app/firmware/firmware_latest.bin"
stdin, stdout, stderr = ssh.exec_command(cmd)
print("CP STDOUT:", stdout.read().decode('utf-8'))
print("CP STDERR:", stderr.read().decode('utf-8'))

cmd2 = "docker exec nala_nas_ws_hub python3 -c \"import os, hashlib, json; fw_dir = '/app/app/firmware'; dst = os.path.join(fw_dir, 'firmware_latest.bin'); content = open(dst, 'rb').read(); meta = {'latest_file': 'firmware_latest.bin', 'original_filename': 'firmware_20261031_184746_firmware_v3.0.0.bin', 'version': 'v3.0.0', 'size_bytes': len(content), 'size_mb': round(len(content)/(1024*1024), 2), 'md5': hashlib.md5(content).hexdigest(), 'upload_time': '2026-10-31 18:47:46', 'download_url': 'http://192.168.1.114:8765/api/ota/firmware/firmware_latest.bin', 'available': True}; json.dump(meta, open(os.path.join(fw_dir, 'ota_meta.json'), 'w', encoding='utf-8'), indent=2); print('SUCCESS', meta['md5'])\""

stdin, stdout, stderr = ssh.exec_command(cmd2)
print("META STDOUT:", stdout.read().decode('utf-8'))
print("META STDERR:", stderr.read().decode('utf-8'))

ssh.close()
