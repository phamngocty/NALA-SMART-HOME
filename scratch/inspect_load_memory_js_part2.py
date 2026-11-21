with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('async function loadMemoryData()')
print(text[idx+1200:idx+3500])
