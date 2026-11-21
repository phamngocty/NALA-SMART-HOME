with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('id="cardGemini"')
if p == -1:
    p = html.find('cfgGeminiKey')
print(html[p-200:p+1200])
