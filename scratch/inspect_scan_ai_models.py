with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('scanAIModels')
print(html[p-50:p+1200])
