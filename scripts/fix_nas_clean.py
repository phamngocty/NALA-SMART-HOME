import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=5)
sftp = ssh.open_sftp()

# 1. FIX INTERCOM ROUTER ON NAS
with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/intercom_router.py', 'r') as f:
    ic_code = f.read().decode('utf-8')

ic_code = ic_code.replace(
    'def unregister(self, device_key: str):',
    'def unregister(self, device_key: str, websocket=None):'
)

with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/intercom_router.py', 'w') as f:
    f.write(ic_code)
print('Fixed intercom_router.py on NAS!')

# 2. RESTORE main_ws_server.py FROM BAK AND APPLY CLEAN SURGICAL PATCH
with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py.bak_stable', 'r') as f:
    srv_code = f.read().decode('utf-8')

srv_code = srv_code.replace('\r\n', '\n')

# Patch on_ha_state_change: DO NOT send giant base_msg to ESP32 panels or default_panel
old_broadcast = """    for dev_id, ws in list(active_sockets.items()):
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
                            "house_status": house_status,
                            "all_rooms": get_all_rooms_summary(local_room=dev.get("room_name", "")),
                            "buttons": get_buttons_with_state(dev, include_all_house_active=False)
                        }
                    }
                    await ws.send_json(panel_msg)
                else:
                    await ws.send_json(base_msg)
        except Exception:
            pass"""

new_broadcast = """    for dev_id, ws in list(active_sockets.items()):
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

assert old_broadcast in srv_code, "old_broadcast not found in NAS original"
srv_code = srv_code.replace(old_broadcast, new_broadcast, 1)

# Patch get_all_rooms_summary: limit each room to 6 devices and total 8 rooms
old_loop = """        room_buttons = []
        for item in a_ents:"""

new_loop = """        room_buttons = []
        for item in a_ents[:6]:"""

assert old_loop in srv_code, "old_loop not found"
srv_code = srv_code.replace(old_loop, new_loop, 1)

old_ret = """    rooms.sort(key=room_sort_key)
    return rooms[:12]"""

new_ret = """    rooms.sort(key=room_sort_key)
    return rooms[:8]"""

assert old_ret in srv_code, "old_ret not found"
srv_code = srv_code.replace(old_ret, new_ret, 1)

with sftp.open('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/main_ws_server.py', 'w') as f:
    f.write(srv_code)
sftp.close()

# 3. RESTART DOCKER
stdin, stdout, stderr = ssh.exec_command('docker restart nala_nas_ws_hub')
print('DOCKER RESTART:', stdout.read().decode())
ssh.close()
print('All NAS fixes applied cleanly!')
