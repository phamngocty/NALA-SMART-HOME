with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

for t in ['role', 'ai', 'ext', 'ha', 'ota']:
    idx = text.find(f'id="tab_sys_{t}"')
    print(f'=== tab_sys_{t} ===')
    if idx != -1:
        print(text[idx:idx+250])
    else:
        print('NOT FOUND!')
