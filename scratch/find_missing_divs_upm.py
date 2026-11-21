with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re

tabs = [
    ('tab_upm_members', 1615),
    ('tab_upm_voiceprint', 1630),
    ('tab_upm_memory', 1813),
    ('tab_upm_test', 1827)
]

for name, start_l in tabs:
    # find where next tab starts
    print(f"\n--- Checking {name} (starting L{start_l}) ---")
    stack = []
    # find tab end
    for i in range(start_l, 1860):
        line = lines[i]
        tags = re.findall(r'(</?div[^>]*>)', line)
        for t in tags:
            if t.startswith('</'):
                if stack:
                    popped = stack.pop()
                else:
                    print(f"  L{i+1}: Extra </div>")
            else:
                stack.append((i+1, t))
        # check if this line closes the tab
        if not stack:
            print(f"  {name} balanced and closed at L{i+1}")
            break
    if stack:
        print(f"  Unclosed in {name}: {len(stack)}")
        for l_num, tag in stack:
            print(f"    L{l_num}: {tag[:80]}")
