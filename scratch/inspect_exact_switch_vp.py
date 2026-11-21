with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('function switchVoiceprintTab')
print(html[idx-100:idx+800])
