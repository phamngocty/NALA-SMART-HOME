with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = re.findall(r'@app\.(?:get|post|delete)\([\"\'](/api/voiceprint[^\"]*)[\"\']', content)
print("Voiceprint endpoints in main_ws_server.py:")
for m in matches:
    print(" -", m)
