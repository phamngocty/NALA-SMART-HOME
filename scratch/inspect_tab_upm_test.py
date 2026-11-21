with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('id="tab_upm_test"')
print(html[idx:idx+1500])
