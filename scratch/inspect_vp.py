with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('voiceprintModal header:')
for l in lines[1852:1885]:
    print(l.rstrip())
