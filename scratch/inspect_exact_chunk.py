with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx1 = html.find('function switchVoiceprintTab')
idx2 = html.find('function refreshVoiceprintData')
print(html[idx1:idx2])
