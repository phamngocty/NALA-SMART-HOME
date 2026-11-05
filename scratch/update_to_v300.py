import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

with open('dashboard_v300.h', 'r', encoding='utf-8') as f:
    content = f.read()

target = '    void update_ring_toggle_ui() {'
rep = '''    void sync_settings(uint8_t vol, uint8_t bright, bool ring, uint8_t mic_gain) {
        if (slider_vol) {
            lv_slider_set_value(slider_vol, vol, LV_ANIM_OFF);
            if (lbl_vol_val) {
                char buf[16];
                snprintf(buf, sizeof(buf), "%d%%", vol);
                lv_label_set_text(lbl_vol_val, buf);
            }
        }
        if (slider_bright) {
            lv_slider_set_value(slider_bright, bright, LV_ANIM_OFF);
            if (lbl_bright_val) {
                char buf[16];
                snprintf(buf, sizeof(buf), "%d%%", bright);
                lv_label_set_text(lbl_bright_val, buf);
            }
        }
        if (slider_mic) {
            lv_slider_set_value(slider_mic, mic_gain, LV_ANIM_OFF);
            if (lbl_mic_val) {
                const char* gain_names[8] = {"", "Thấp", "Vừa", "Chuẩn", "Nhạy", "Rất nhạy", "Cực nhạy", "Tối đa"};
                char m_buf[32];
                snprintf(m_buf, sizeof(m_buf), "Mức %d (%s)", mic_gain, (mic_gain >= 1 && mic_gain <= 7) ? gain_names[mic_gain] : "");
                lv_label_set_text(lbl_mic_val, m_buf);
            }
        }
        ring_on_call_enabled = ring;
        update_ring_toggle_ui();
    }

    void update_ring_toggle_ui() {'''

if target in content:
    content = content.replace(target, rep)
    with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'w', encoding='utf-8') as out:
        out.write(content)
    print('Updated firmware_esp32s3_panel/include/ui_lvgl_dashboard.h to v3.0.0 successfully!')
else:
    print('Target not found!')

# In main.cpp, set CURRENT_FIRMWARE_VERSION to "v3.0.0"
with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    main_c = f.read()

import re
main_c = re.sub(r'#define\s+CURRENT_FIRMWARE_VERSION\s+"[^"]+"', '#define CURRENT_FIRMWARE_VERSION "v3.0.0"', main_c)

with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
    f.write(main_c)

print('Updated main.cpp firmware version to v3.0.0!')
