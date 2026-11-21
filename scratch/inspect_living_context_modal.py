with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="livingContextAutomationModal"')
end = html.find('id="communicationModal"')
print(html[start:end])
