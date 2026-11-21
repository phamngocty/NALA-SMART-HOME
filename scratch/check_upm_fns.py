with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

for fn in ['loadVoiceprintSpeakers', 'loadSpeakersList', 'loadHistoryForVoiceprint', 'loadMemoryData']:
    found = f'function {fn}' in html or f'{fn} =' in html
    print(f"{fn}: {'FOUND' if found else '❌ NOT FOUND'}")
