with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2129, 2200):
    print(f'{i+1}: {lines[i]}', end='')
