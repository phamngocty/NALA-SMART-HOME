with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', text)
from collections import Counter
counts = Counter(matches)
duplicates = {k: v for k, v in counts.items() if v > 1}
print("Duplicate functions:", duplicates)

# Find line numbers of duplicates
lines = text.split('\n')
for dup in duplicates:
    print(f"\nDuplicate: {dup}")
    for idx, line in enumerate(lines):
        if re.search(rf'function\s+{dup}\s*\(', line):
            print(f"  Line {idx+1}: {line.strip()[:100]}")
