with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('value="openrouter"')
print(html[p-100:p+400])
