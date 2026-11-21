with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('const XZ_VOICES =')
if idx != -1:
    print(content[idx:idx+1200])
else:
    print("XZ_VOICES not found")
