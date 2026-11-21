with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
for m in re.finditer(r'id="tab_sys_role_btn"', html):
    print("tab_sys_role_btn at", m.start())

for m in re.finditer(r'id="tab_sys_role"', html):
    print("tab_sys_role at", m.start())

for m in re.finditer(r'id="systemSettingsModal"', html):
    print("systemSettingsModal at", m.start())
