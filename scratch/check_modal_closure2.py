with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx_ota = html.find('id="tab_sys_ota"')
print(html[idx_ota+3000:idx_ota+4500])
