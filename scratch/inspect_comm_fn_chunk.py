with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx1 = html.find('function switchCommunicationTab')
idx2 = html.find('function openSystemSettingsModal', idx1)
print(html[idx1:idx2])
