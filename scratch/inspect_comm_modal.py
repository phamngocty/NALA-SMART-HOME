with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="communicationModal"')
end = html.find('id="systemSettingsModal"')
print(html[start:end])
