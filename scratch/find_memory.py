with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'nalaMemoryModal' in l:
        print(f"nalaMemoryModal at line {i+1}")
        print(''.join(lines[i:i+80]))
        break
