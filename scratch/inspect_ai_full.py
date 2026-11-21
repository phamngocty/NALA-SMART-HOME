with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

p_ai = text.find('id="tab_sys_ai"')
p_ota = text.find('id="tab_sys_ota"')
print(text[p_ai:p_ota])
