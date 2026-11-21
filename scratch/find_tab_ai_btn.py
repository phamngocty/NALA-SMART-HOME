with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('tab_sys_ai_btn')
print(repr(content[idx-40:idx+250]))
