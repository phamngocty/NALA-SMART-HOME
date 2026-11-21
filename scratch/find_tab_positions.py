with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("tab_sys_role at:", html.find('id="tab_sys_role"'))
print("tab_sys_ai at:", html.find('id="tab_sys_ai"'))
print("tab_sys_ha at:", html.find('id="tab_sys_ha"'))
print("tab_sys_ota at:", html.find('id="tab_sys_ota"'))
