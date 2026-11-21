with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i in range(2094, 3187):
    line = lines[i]
    # tokenise tags
    import re
    tags = re.findall(r'(</?div[^>]*>)', line)
    for t in tags:
        if t.startswith('</'):
            if stack:
                popped = stack.pop()
                # print if popped was an important container
                if any(x in popped for x in ['id=', 'class="modal-']):
                    print(f"L{i+1}: Closes [{popped.strip()[:60]}] | remaining stack: {len(stack)}")
            else:
                print(f"L{i+1}: Extra </div>")
        else:
            stack.append(f"L{i+1}: {t}")
            if any(x in t for x in ['id=', 'class="modal-']):
                print(f"L{i+1}: Opens  [{t.strip()[:60]}] | stack depth: {len(stack)}")

print("Remaining open divs at line 3187:", len(stack))
for s in stack:
    print("  ", s)
