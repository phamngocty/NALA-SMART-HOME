import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Find all modals
modals = re.findall(r'<div[^>]*class=["\'][^"\']*modal-overlay[^"\']*["\'][^>]*id=["\']([^"\']+)["\']', text)
print("=== CÁC MODAL HIỆN TẠI ===")
for m in modals:
    print(f"- {m}")

# Find sections on page
print("\n=== CÁC KHU VỰC TRÊN TRANG CHÍNH ===")
lines = text.splitlines()
for i, l in enumerate(lines[:1800]):
    if '<section' in l or 'class="kpi-row"' in l or 'floor-tree' in l or 'class="section' in l or '<header' in l:
        print(f"L{i+1}: {l.strip()[:90]}")
