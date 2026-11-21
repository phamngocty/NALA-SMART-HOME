with open('server_nas_hub/app/ha_bridge.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('media_player')
print(content[idx-50:idx+400])
