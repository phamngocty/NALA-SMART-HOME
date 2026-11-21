with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(1840, 1875):
    print(f"L{i+1}: {lines[i]}", end="")
