with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Check loadVoiceprintSpeakers, loadHistoryForVoiceprint, loadMemoryData
for fn in ['loadVoiceprintSpeakers', 'loadHistoryForVoiceprint', 'loadMemoryData']:
    idx = html.find(f'async function {fn}')
    if idx == -1:
        idx = html.find(f'function {fn}')
    print(f"=== {fn} ===")
    print(html[idx:idx+400])
