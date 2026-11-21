with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re
ota_routes = re.findall(r'@app\.[a-z]+\(["\'](/api/ota[^"\']*)["\']', text)
ext_routes = re.findall(r'@app\.[a-z]+\(["\'](/api/ext[^"\']*)["\']', text)
print('OTA routes:', ota_routes)
print('Extension routes:', ext_routes)

# Also check what loadOTAData and loadExtensionData call in index.html
with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

for fn in ['loadOTAData', 'loadExtensionData']:
    idx = html.find(f'function {fn}')
    print(f"\n=== {fn} in index.html ===")
    print(html[idx:idx+400])
