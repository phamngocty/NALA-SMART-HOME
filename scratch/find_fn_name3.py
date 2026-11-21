with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find("fetch('/api/ai/models'")
print(html[p-1400:p-800])
