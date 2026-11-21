with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('/api/voiceprint/enroll')
print(content[idx+2000:idx+3500])
