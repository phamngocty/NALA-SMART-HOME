with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'function escapeHtml', text)]
for idx in matches:
    print(text[idx:idx+250])
    print("="*40)
