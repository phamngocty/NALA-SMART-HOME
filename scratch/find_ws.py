with open('server_nas_hub/app/static/index.html', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if '.onmessage' in line or 'onWsMessage' in line:
        print(f"Line {i+1}: {line.strip()[:100]}")
