with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="sub_vp_hist_panel"')
print(content[idx:idx+3500])
