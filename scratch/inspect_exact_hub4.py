with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx1 = html.find('// HUB 4: CÀI ĐẶT KỸ THUẬT & PHẦN CỨNG')
idx2 = html.find('// --- XIAOZHI VOICE ROLE')
print(html[idx1:idx2])
