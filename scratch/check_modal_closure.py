with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx_modal = html.find('id="systemSettingsModal"')
idx_ota = html.find('id="tab_sys_ota"')

# Find where tab_sys_ota ends
print(html[idx_ota+1500:idx_ota+3000])
