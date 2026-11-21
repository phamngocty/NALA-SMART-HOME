with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

for fn in ['loadHAConfig', 'loadOTAFiles', 'loadAIConfig', 'loadXiaoZhiVoiceRole']:
    idx = html.find(f'function {fn}')
    print(f"{fn}: {'FOUND' if idx != -1 else '❌ NOT FOUND'}")
