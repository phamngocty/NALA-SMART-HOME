with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="systemSettingsModal"')
print(content[idx+1200:idx+2500])
