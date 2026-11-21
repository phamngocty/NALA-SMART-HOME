with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="tab_vp_enroll"')
print(content[idx+8500:idx+11500])
