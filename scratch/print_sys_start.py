with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2094, 2135):
    print(f"{i+1}: {lines[i]}", end="")
