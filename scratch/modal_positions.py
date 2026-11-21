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
    print(f"Modal {m} starts at character {idx}")
