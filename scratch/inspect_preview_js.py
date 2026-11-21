with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function playVoicePreviewItem')
if idx != -1:
    print(content[idx:idx+1500])
else:
    print("playVoicePreviewItem not found")
