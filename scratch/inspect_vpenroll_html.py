with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('vpEnrollName')
print(content[idx-100:idx+2500])
