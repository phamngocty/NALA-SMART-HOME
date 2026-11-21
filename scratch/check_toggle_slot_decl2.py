with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function toggleSlotRecording')
print(content[idx-20:idx+60])
