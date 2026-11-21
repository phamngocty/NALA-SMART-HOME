with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def convert_audio_to_pcm16k')
print(content[idx:idx+1500])
