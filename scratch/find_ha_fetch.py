with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r"fetch\(.*api/ha/config", html)]
print("fetch('/api/ha/config') at:", matches)
for m in matches:
    print(html[m-100:m+400])
