with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('id="tab_sys_ai"')
print(html[p:p+3000])
