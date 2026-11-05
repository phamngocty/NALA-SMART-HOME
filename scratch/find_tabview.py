import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'lv_tabview_create' in line or 'tabview' in line:
            print(f'{i+1}: {line.strip()[:100]}')
