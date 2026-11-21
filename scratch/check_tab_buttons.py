with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

modals = [
    'userProfileMemoryModal',
    'livingContextAutomationModal',
    'communicationModal',
    'systemSettingsModal'
]

for m in modals:
    idx = text.find(f'id="{m}"')
    chunk = text[idx:idx+4000]
    # find all wizard-tab elements in header
    tabs = re.findall(r'<div[^>]*class=["\'][^"\']*wizard-tab[^"\']*["\'][^>]*id=["\']([^"\']+)["\'][^>]*>', chunk)
    print(f"\nModal {m} tab buttons:")
    for t in tabs:
        print(f"  {t}")
