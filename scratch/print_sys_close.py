with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for idx in range(3174, 3187):
    print(f"{idx+1}: {lines[idx]}", end="")
