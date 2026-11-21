with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="userProfileMemoryModal"')
end = html.find('id="livingContextAutomationModal"')
modal_html = html[start:end]

import re
divs_with_id = re.findall(r'<div[^>]*id=["\']([^"\']+)["\'][^>]*>', modal_html)
print("Divs with IDs in userProfileMemoryModal:")
for d in divs_with_id:
    if 'tab' in d or 'vp' in d:
        print(" ->", d)
