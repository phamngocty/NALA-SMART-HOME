import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)
sftp = ssh.open_sftp()

with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py', 'r') as f:
    code = f.read().decode('utf-8')

code = code.replace('\r\n', '\n')

old_block = """    for dev_id, ws in list(active_sockets.items()):
        try:
            if dev_id.startswith("web_admin"):
                await ws.send_json(base_msg)
            else:
                # Gửi cho màn hình ESP32: kèm buttons và all_rooms ưu tiên phòng hiện tại
                dev = devices_db.get(dev_id)
                if dev:
                    panel_msg = {
                        "type": "ha_state_change",
                        "payload": {
                            "entity_id": entity_id,
                            "state": new_state,
                            "is_on": is_on,
                            "attributes": attrs,
                            "house_status": house_status
                        }
                    }
                    await ws.send_json(panel_msg)
                else:
                    await ws.send_json(base_msg)
        except Exception:
            pass"""

new_block = """    for dev_id, ws in list(active_sockets.items()):
        try:
            if dev_id.startswith("web_admin"):
                await ws.send_json(base_msg)
            elif dev_id == "default_panel":
                continue
            else:
                panel_msg = {
                    "type": "ha_state_change",
                    "payload": {
                        "entity_id": entity_id,
                        "state": new_state,
                        "is_on": is_on,
                        "attributes": attrs,
                        "house_status": house_status
                    }
                }
                await ws.send_json(panel_msg)
        except Exception:
            pass"""

assert old_block in code, "old_block not found"
code = code.replace(old_block, new_block, 1)

with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py', 'w') as f:
    f.write(code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print('DOCKER RESTART:', stdout.read().decode())
ssh.close()
print('Fix applied: default_panel eliminated from base_msg broadcast!')
