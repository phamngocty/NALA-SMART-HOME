import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2065, 2140):
    if i < len(lines):
        print(f'{i+1}: {lines[i]}', end='')
