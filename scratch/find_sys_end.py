with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(3130, 3230):
    if idx < len(lines):
        print(f"{idx+1}: {lines[idx]}", end="")
