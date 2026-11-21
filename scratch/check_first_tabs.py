with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

first_tabs = [
    'tab_upm_members_btn',
    'tab_lc_fsm_btn',
    'tab_comm_intercom_btn',
    'tab_sys_role_btn'
]

for t in first_tabs:
    idx = text.find(f'id="{t}"')
    if idx != -1:
        print(text[idx-20:idx+60])
