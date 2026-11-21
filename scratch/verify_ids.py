import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Check duplicate IDs
ids = re.findall(r'id=["\']([^"\']+)["\']', text)
seen = set()
duplicates = set()
for i in ids:
    if i in seen:
        duplicates.add(i)
    seen.add(i)

print(f"Total IDs: {len(ids)}, Unique IDs: {len(seen)}")
if duplicates:
    print("Warning: Duplicate IDs found:", duplicates)
else:
    print("✅ No duplicate IDs found!")

# Check if 4 modals exist
for mid in ['userProfileMemoryModal', 'livingContextAutomationModal', 'communicationModal', 'systemSettingsModal']:
    assert f'id="{mid}"' in text, f"Missing modal {mid}!"
print("✅ All 4 unified modals are present!")
