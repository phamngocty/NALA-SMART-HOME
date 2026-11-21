with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function saveXiaoZhiVoiceRole')
if idx != -1:
    print(content[idx-500:idx+2500])
else:
    print("saveXiaoZhiVoiceRole not found")
