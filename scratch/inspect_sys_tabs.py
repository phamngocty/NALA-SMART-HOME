with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_sys = text.find('id="systemSettingsModal"')
chunk = text[idx_sys:idx_sys+15000]

# find all tab_sys_
import re
tabs = re.findall(r'id="(tab_sys_[a-z]+)"[^>]*style="([^"]*)"', chunk)
print("System Settings Tabs and their styles:")
for t, s in tabs:
    print(f"  {t}: style='{s}'")
