with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="tab_upm_voiceprint"')
print(content[idx:idx+3500])
