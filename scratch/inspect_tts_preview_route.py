with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('/api/tts/preview')
if idx != -1:
    print(content[idx:idx+1200])
else:
    print("Not found")
