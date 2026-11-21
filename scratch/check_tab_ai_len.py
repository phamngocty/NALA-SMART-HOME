with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('id="tab_sys_ai"')
end = text.find('id="tab_sys_ota"')
print('Length of tab_sys_ai:', end - start)
