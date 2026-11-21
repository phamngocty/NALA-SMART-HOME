with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
import re

for i in range(1582, 1862):
    line = lines[i]
    tags = re.findall(r'(</?div[^>]*>)', line)
    for t in tags:
        if t.startswith('</'):
            if stack:
                stack.pop()
            else:
                print(f"L{i+1}: Extra </div>")
        else:
            stack.append((i+1, t))

print(f"Stack remaining at L1861: {len(stack)}")
for line_no, tag in stack:
    print(f"  Unclosed from L{line_no}: {tag[:80]}")
