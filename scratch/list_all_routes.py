import re

with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    text = f.read()

get_routes = re.findall(r'@app\.(get|post|delete|put)\(["\']([^"\']+)["\']', text)
print(f"Total routes in main_ws_server.py: {len(get_routes)}")
for method, path in sorted(get_routes):
    print(f"{method.upper():6} {path}")
