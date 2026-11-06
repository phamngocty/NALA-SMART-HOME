with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = c.replace('\r\n', '\n')
old_p = """                    panel_msg = {
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
                    }"""

new_p = """                    panel_msg = {
                        "type": "ha_state_change",
                        "payload": {
                            "entity_id": entity_id,
                            "state": new_state,
                            "is_on": is_on,
                            "attributes": attrs,
                            "house_status": house_status
                        }
                    }"""

assert old_p in c, 'old_p not found'
c = c.replace(old_p, new_p, 1)

old_ret = """    rooms.sort(key=room_sort_key)
    return rooms[:12]"""

new_ret = """    rooms.sort(key=room_sort_key)
    return rooms[:8]"""

assert old_ret in c, 'old_ret not found'
c = c.replace(old_ret, new_ret, 1)

with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Local main_ws_server.py updated successfully!')
