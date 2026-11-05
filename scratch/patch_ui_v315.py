import re

path = 'firmware_esp32s3_panel/include/ui_lvgl_dashboard.h'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Clear scrollable flag on tabview content and add event callbacks
pattern1 = r'(lv_obj_set_style_text_font\(tab_btns, &font_vietnamese_14, 0\);)'
replace1 = r'''\1
        lv_obj_clear_flag(lv_tabview_get_content(tabview), LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(tab_btns, event_handler_trampoline, LV_EVENT_ALL, this);
        lv_obj_add_event_cb(tabview, event_handler_trampoline, LV_EVENT_ALL, this);'''

text, cnt1 = re.subn(pattern1, replace1, text)
print(f"Patch 1 (Tabview events): {cnt1}")
assert cnt1 == 1, "Failed to patch tabview setup!"

# 2. Add event logging and tab handling in handle_event
pattern2 = r'(\s+lv_obj_t\* target = lv_event_get_target\(e\);\s+lv_event_code_t code = lv_event_get_code\(e\);)'
replace2 = r'''\1

        if (code == LV_EVENT_CLICKED) {
            Serial.printf("[UI-EVENT] CLICKED target=%p\n", target);
        } else if (code == LV_EVENT_VALUE_CHANGED) {
            Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p\n", target);
        }

        // Tab changes
        if ((target == tabview || target == lv_tabview_get_tab_btns(tabview)) && code == LV_EVENT_VALUE_CHANGED) {
            uint32_t act_tab = lv_tabview_get_tab_act(tabview);
            const char* names[] = {"Thiết Bị", "Nala AI", "Đàm Thoại", "Cài Đặt"};
            const char* n = (act_tab < 4) ? names[act_tab] : "Khác";
            Serial.printf("[UI-TAB] Chuyen sang Tab %u: %s\n", (unsigned int)act_tab, n);
        }'''

text, cnt2 = re.subn(pattern2, replace2, text, count=1)
print(f"Patch 2 (Event logs): {cnt2}")
assert cnt2 == 1, "Failed to patch handle_event logging!"

# 3. Add Serial logs for chip_all and device buttons
text = text.replace(
    'if (target == chip_all && code == LV_EVENT_CLICKED) {',
    'if (target == chip_all && code == LV_EVENT_CLICKED) {\n            Serial.println("[UI-ACTION] Clicked TOÀN NHÀ chip!");'
)

old_btn_code = '''            if (target == buttons[i].btn_obj && code == LV_EVENT_CLICKED) {
                bool is_climate = (buttons[i].icon == "climate" || buttons[i].entity_id.startsWith("climate"));'''

new_btn_code = '''            if (target == buttons[i].btn_obj && code == LV_EVENT_CLICKED) {
                Serial.printf("[UI-ACTION] Clicked Button %d (%s) entity=%s is_on=%d\\n", 
                              i, buttons[i].name.c_str(), buttons[i].entity_id.c_str(), (int)buttons[i].is_on);
                bool is_climate = (buttons[i].icon == "climate" || buttons[i].entity_id.startsWith("climate"));'''

assert old_btn_code.replace('\r\n', '\n') in text.replace('\r\n', '\n'), "old_btn_code not found!"
text = text.replace('\r\n', '\n').replace(old_btn_code.replace('\r\n', '\n'), new_btn_code.replace('\r\n', '\n'))

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

print("ui_lvgl_dashboard.h patched successfully!")
