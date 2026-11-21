with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('pcm_to_text')
if idx != -1:
    print(content[idx-100:idx+600])
else:
    print("pcm_to_text not found")
