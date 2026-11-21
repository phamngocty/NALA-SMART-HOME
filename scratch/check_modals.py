with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

tabs_to_check = [
    # Hub 1 (Hồ sơ & Trí nhớ)
    'tab_upm_members', 'tab_upm_voiceprint', 'tab_upm_memory', 'tab_upm_test',
    # Hub 2 (Tự động hóa ngữ cảnh)
    'tab_lc_fsm', 'tab_lc_rules',
    # Hub 3 (Giao tiếp & Lịch sử)
    'tab_comm_intercom', 'tab_comm_history',
    # Hub 4 (Cài đặt kỹ thuật & XiaoZhi Console)
    'tab_sys_role', 'tab_sys_ai', 'tab_sys_vp', 'tab_sys_ext', 'tab_sys_ha', 'tab_sys_ota'
]
all_ok = True
for t in tabs_to_check:
    div_found = f'id="{t}"' in content
    btn_id = f'{t}_btn'
    btn_found = f'id="{btn_id}"' in content
    if not (div_found and btn_found):
        all_ok = False
        print(f'❌ Tab {t}: div={div_found}, btn={btn_found}')
    else:
        print(f'✅ Tab {t}: OK')

print("All tabs verified:", all_ok)
