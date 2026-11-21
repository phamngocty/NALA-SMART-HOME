with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'modal-overlay' in l and 'id=' in l:
        print(f"L{i+1}: {l.strip()[:100]}")
