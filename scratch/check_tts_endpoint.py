with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

print('/api/tts/preview' in content)
idx = content.find('tts')
print('Found tts in main_ws_server at:', idx)
if '/api/tts' in content:
    idx2 = content.find('/api/tts')
    print(content[idx2:idx2+400])
