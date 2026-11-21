with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

modals = [
    'userProfileMemoryModal',
    'livingContextAutomationModal',
    'communicationModal',
    'systemSettingsModal'
]

import re

for m in modals:
    print(f"\n=================== TRACING {m} ===================")
    # find line where id=m is opened
    start_line = None
    for i, line in enumerate(lines):
        if f'id="{m}"' in line:
            start_line = i
            break
    
    if start_line is None:
        print(f"Modal {m} NOT FOUND!")
        continue

    depth = 0
    closed_at = None
    for i in range(start_line, len(lines)):
        line = lines[i]
        tags = re.findall(r'(</?div[^>]*>)', line)
        for t in tags:
            if t.startswith('</'):
                depth -= 1
                if depth == 0:
                    closed_at = i
                    break
            else:
                depth += 1
        if closed_at is not None:
            break
    
    print(f"Modal {m} opened at L{start_line+1}, closed at L{closed_at+1 if closed_at is not None else 'NEVER CLOSED!'}")
    if closed_at is not None:
        print("  Snippet around closing:")
        for k in range(max(start_line, closed_at-5), min(len(lines), closed_at+5)):
            prefix = "==>" if k == closed_at else "   "
            print(f"{prefix} L{k+1}: {lines[k].strip()[:90]}")
    else:
        print(f"  ❌ FATAL: Modal {m} is NEVER CLOSED!")
