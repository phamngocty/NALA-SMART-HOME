import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's verify start and end lines of modals
modals = [
    'installerModal',
    'haConfigModal',
    'otaManagerModal',
    'intercomModal',
    'historyModal',
    'voiceprintModal',
    'automationEditorModal',
    'climateModal',
    'aiConfigModal',
    'nalaMemoryModal',
    'allHouseConfigModal'
]

lines = text.splitlines()
positions = {}
for i, l in enumerate(lines):
    for m in modals:
        if f'id="{m}"' in l:
            positions[m] = i + 1

for m in modals:
    print(f"{m}: starts at line {positions.get(m)}")
