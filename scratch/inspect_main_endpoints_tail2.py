with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('/api/tts/preview')
print(content[idx+2400:idx+3200])
