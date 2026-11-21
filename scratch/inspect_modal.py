import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for m in re.finditer(r'id=["\'](tab_sys_[^"\']+)["\']', text):
    print(f"Found {m.group(1)} at char {m.start()}")

# Find modal containers
for m in re.finditer(r'id=["\']([a-zA-Z0-9_]*Modal)["\']', text):
    print(f"Modal: {m.group(1)} at char {m.start()}")
