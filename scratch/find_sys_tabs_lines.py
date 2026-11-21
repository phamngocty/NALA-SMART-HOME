with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    for t in ['tab_sys_role', 'tab_sys_ai', 'tab_sys_ext', 'tab_sys_ha', 'tab_sys_ota']:
        if f'id="{t}"' in line:
            print(f"Line {idx+1}: {line.strip()[:100]}")
