with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('toggleSlotRecording')
print(content[idx-30:idx+80])
