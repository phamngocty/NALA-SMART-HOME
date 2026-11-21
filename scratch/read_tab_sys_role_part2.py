with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()
idx = text.find('id="tab_sys_role"')
if idx != -1:
    print(text[idx+2500:idx+6500])
