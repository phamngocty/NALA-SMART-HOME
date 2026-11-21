with open('server_nas_hub/app/static/index.html', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[1830:1920]):
    print(f"Line {1830+i+1}: {line.strip()[:100]}")
