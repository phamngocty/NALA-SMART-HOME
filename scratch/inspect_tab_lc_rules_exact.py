with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="tab_lc_rules"')
print(text[idx:idx+1200])
