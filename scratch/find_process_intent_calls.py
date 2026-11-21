with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = [m.start() for m in re.finditer(r'process_intent\(', content)]
print("process_intent calls:", len(matches))
for pos in matches[:3]:
    print("--- snippet ---")
    print(content[pos-50:pos+150])
