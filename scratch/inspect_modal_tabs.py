with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re

for modal in ['systemSettingsModal', 'userProfileMemoryModal']:
    idx = content.find(f'id="{modal}"')
    if idx != -1:
        modal_chunk = content[idx:idx+3000]
        tab_buttons = re.findall(r'<div[^>]*class="[^"]*hub-tab[^"]*"[^>]*>.*?</div>', modal_chunk, re.DOTALL)
        print(f"Tabs inside {modal}:")
        for tb in tab_buttons:
            print("  ", tb.strip().replace('\n', ' '))
