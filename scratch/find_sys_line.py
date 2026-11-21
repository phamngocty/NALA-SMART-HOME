with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'id="systemSettingsModal"' in l:
        print(f"systemSettingsModal at line {i+1}: {l.strip()}")
