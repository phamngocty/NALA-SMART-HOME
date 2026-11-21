with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
functions = re.findall(r'function (?:enroll|loadHistory|recordSlot|stopSlot|playSlot)[^\(]*\(', content)
print("Related functions in index.html:")
for f in set(functions):
    print(" -", f)
