with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function switchVoiceprintSubMode')
print(content[idx:idx+1500])
