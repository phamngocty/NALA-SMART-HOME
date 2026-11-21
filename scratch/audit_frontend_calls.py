import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all fetch calls in javascript
fetches = re.findall(r'fetch\(["\']([^"\']+)["\']', html)
print(f"Total fetch calls in index.html: {len(fetches)}")
unique_fetches = sorted(set(fetches))
for u in unique_fetches:
    print("FETCH:", u)
