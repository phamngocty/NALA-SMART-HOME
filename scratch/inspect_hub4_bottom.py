with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('// HUB 4: CÀI ĐẶT KỸ THUẬT & PHẦN CỨNG')
print(html[idx:idx+1800])
