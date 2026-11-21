with open('server_nas_hub/app/static/index.html', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
for i, line in enumerate(lines):
    if any(k in line for k in ['<div class="card', '<section', 'id="card', 'id="sec', '<h2>', '<h2 ']):
        print(f"Line {i+1}: {line.strip()[:110]}")
