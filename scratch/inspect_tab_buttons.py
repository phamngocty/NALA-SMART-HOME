with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="tab_sys_ota_btn"')
print(content[idx-200:idx+400])
