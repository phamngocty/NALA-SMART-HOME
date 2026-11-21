with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx_modal = html.find('id="systemSettingsModal"')
idx_ext = html.find('id="tab_sys_ext"')
idx_ha = html.find('id="tab_sys_ha"')
idx_ota = html.find('id="tab_sys_ota"')

print("systemSettingsModal at:", idx_modal)
print("tab_sys_ext at:", idx_ext, "(distance from modal:", idx_ext - idx_modal, ")")
print("tab_sys_ha at:", idx_ha, "(distance from modal:", idx_ha - idx_modal, ")")
print("tab_sys_ota at:", idx_ota, "(distance from modal:", idx_ota - idx_modal, ")")
