with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="tab_sys_role"')
if idx != -1:
    print(content[idx+2000:idx+6000])
