with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
header_buttons = re.findall(r'<button[^>]*onclick="open[^"]*"[^>]*>.*?</button>', content, re.DOTALL)
print("Top Nav Buttons:")
for b in header_buttons:
    print(b.strip().replace('\n', ' '))
