with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function blobToBase64')
if idx != -1:
    print(content[idx:idx+500])
else:
    print("blobToBase64 not found")
