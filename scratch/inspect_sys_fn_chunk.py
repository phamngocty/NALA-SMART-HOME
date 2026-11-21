with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx1 = html.find('function switchSystemSettingsTab')
idx2 = html.find('// --- XIAOZHI VOICE ROLE', idx1)
print(html[idx1:idx2])
