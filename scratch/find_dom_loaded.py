with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'DOMContentLoaded' in line or 'window.onload' in line:
        print(f"Line {i+1}: {line.strip()}")
        for j in range(max(0, i-5), min(len(lines), i+25)):
            print(f"  {j+1}: {lines[j].rstrip()}")
        print("-" * 50)
