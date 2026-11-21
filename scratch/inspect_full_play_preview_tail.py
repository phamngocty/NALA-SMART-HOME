with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function playVoicePreviewItem')
print(content[idx+700:idx+1500])
