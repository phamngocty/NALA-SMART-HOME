with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function openSystemSettingsModal')
print(content[idx:idx+800])
idx2 = content.find('function switchSystemSettingsTab')
print(content[idx2:idx2+800])
