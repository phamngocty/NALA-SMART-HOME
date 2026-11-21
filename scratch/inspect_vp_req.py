with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('class VoiceprintEnrollRequest')
print(content[idx:idx+600])
