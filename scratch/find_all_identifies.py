with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r'\.identify\(', content)]
print("identify calls in main_ws_server:", len(matches))
for pos in matches:
    print("--- snippet ---")
    print(content[pos-100:pos+250])
