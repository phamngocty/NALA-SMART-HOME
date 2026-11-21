with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('Lines 1215-1255 in index.html:')
for i, l in enumerate(lines[1214:1255]):
    print(f"L{1215+i}: {l.rstrip()}")
