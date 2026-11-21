with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="tab_sys_role"' in l:
        print('tab_sys_role start line:', i+1)
    if 'id="tab_sys_ai"' in l:
        print('tab_sys_ai start line:', i+1)
