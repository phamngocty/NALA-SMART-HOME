import re

# 1. Update ui_lvgl_dashboard.h
with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'r', encoding='utf-8') as f:
    code = f.read()

# Add member variables
target_members = '''    // Incoming Call Modal
    lv_obj_t* modal_incoming_call;
    lv_obj_t* lbl_incoming_title;
    lv_obj_t* lbl_incoming_caller;
    lv_obj_t* lbl_incoming_status;'''

repl_members = '''    // Incoming Call Modal
    lv_obj_t* modal_incoming_call;
    lv_obj_t* lbl_incoming_title;
    lv_obj_t* lbl_incoming_caller;
    lv_obj_t* lbl_incoming_status;

    // Screensaver Standby Modal (Smart Clock Watchface)
    lv_obj_t* modal_screensaver;
    lv_obj_t* lbl_stb_time;
    lv_obj_t* lbl_stb_sec;
    lv_obj_t* lbl_stb_date;
    lv_obj_t* lbl_stb_room;
    lv_obj_t* lbl_stb_clim;
    lv_obj_t* lbl_stb_hint;
    bool screensaver_active;'''

# Add constructor init
target_ctor = '''          dialog_climate(nullptr), lbl_clim_title(nullptr), btn_clim_close(nullptr),'''
repl_ctor = '''          modal_screensaver(nullptr), lbl_stb_time(nullptr), lbl_stb_sec(nullptr),
          lbl_stb_date(nullptr), lbl_stb_room(nullptr), lbl_stb_clim(nullptr),
          lbl_stb_hint(nullptr), screensaver_active(false),
          dialog_climate(nullptr), lbl_clim_title(nullptr), btn_clim_close(nullptr),'''

# Add build_screensaver call in init()
target_init_call = '''        build_incoming_call_modal(scr);
        build_climate_dialog(scr);
    }'''

repl_init_call = '''        build_incoming_call_modal(scr);
        build_climate_dialog(scr);
        build_screensaver(scr);
    }'''

# Add handle_event click
target_event = '''        if (code == LV_EVENT_CLICKED) {
            Serial.printf("[UI-EVENT] CLICKED target=%p\\n", target);
        }'''

repl_event = '''        if (code == LV_EVENT_CLICKED) {
            Serial.printf("[UI-EVENT] CLICKED target=%p\\n", target);
            if (target == modal_screensaver) {
                hide_screensaver();
                return;
            }
        }'''

# Add build_screensaver definition and methods right after hide_incoming_call()
target_methods = '''    void hide_incoming_call() {
        if (modal_incoming_call) {
            lv_obj_add_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);
        }
    }'''

repl_methods = '''    void hide_incoming_call() {
        if (modal_incoming_call) {
            lv_obj_add_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);
        }
    }

    void build_screensaver(lv_obj_t* parent) {
        modal_screensaver = lv_obj_create(parent);
        lv_obj_set_size(modal_screensaver, 240, 320);
        lv_obj_set_pos(modal_screensaver, 0, 0);
        lv_obj_set_style_bg_color(modal_screensaver, lv_color_hex(0x05070D), 0); // Apple Deep Dark Standby
        lv_obj_set_style_border_width(modal_screensaver, 0, 0);
        lv_obj_set_style_radius(modal_screensaver, 0, 0);
        lv_obj_set_style_pad_all(modal_screensaver, 4, 0);
        lv_obj_clear_flag(modal_screensaver, LV_OBJ_FLAG_SCROLLABLE);

        // Mặc định ẩn hoàn toàn khi khởi động (Bảo toàn 100% bố cục gốc)
        lv_obj_add_flag(modal_screensaver, LV_OBJ_FLAG_HIDDEN);

        // Bắt sự kiện chạm để mở lại Dashboard
        lv_obj_add_event_cb(modal_screensaver, event_handler_trampoline, LV_EVENT_CLICKED, this);

        // Top: Tên phòng hiện tại
        lbl_stb_room = lv_label_create(modal_screensaver);
        lv_label_set_text_fmt(lbl_stb_room, "📍 %s", home_room_name);
        lv_obj_set_style_text_color(lbl_stb_room, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_stb_room, &font_vietnamese_14, 0);
        lv_obj_align(lbl_stb_room, LV_ALIGN_TOP_MID, 0, 16);

        // Center: Giờ số to (Font Montserrat 32px)
        lbl_stb_time = lv_label_create(modal_screensaver);
        lv_label_set_text(lbl_stb_time, "00:00");
        lv_obj_set_style_text_color(lbl_stb_time, lv_color_hex(0xFFFFFF), 0);
        lv_obj_set_style_text_font(lbl_stb_time, &lv_font_montserrat_32, 0);
        lv_obj_align(lbl_stb_time, LV_ALIGN_CENTER, 0, -32);

        // Giây
        lbl_stb_sec = lv_label_create(modal_screensaver);
        lv_label_set_text(lbl_stb_sec, ":00");
        lv_obj_set_style_text_color(lbl_stb_sec, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_stb_sec, &font_vietnamese_14, 0);
        lv_obj_align(lbl_stb_sec, LV_ALIGN_CENTER, 0, -4);

        // Thứ, Ngày Tháng Năm Tiếng Việt
        lbl_stb_date = lv_label_create(modal_screensaver);
        lv_label_set_text(lbl_stb_date, "Chờ đồng bộ giờ...");
        lv_obj_set_style_text_color(lbl_stb_date, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_stb_date, &font_vietnamese_14, 0);
        lv_obj_align(lbl_stb_date, LV_ALIGN_CENTER, 0, 24);

        // Nhiệt độ phòng / Trạng thái
        lbl_stb_clim = lv_label_create(modal_screensaver);
        lv_label_set_text(lbl_stb_clim, "❄️ Nala Smart Home");
        lv_obj_set_style_text_color(lbl_stb_clim, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_stb_clim, &font_vietnamese_14, 0);
        lv_obj_align(lbl_stb_clim, LV_ALIGN_CENTER, 0, 56);

        // Gợi ý chạm
        lbl_stb_hint = lv_label_create(modal_screensaver);
        lv_label_set_text(lbl_stb_hint, "Chạm màn hình để mở");
        lv_obj_set_style_text_color(lbl_stb_hint, lv_color_hex(0x475569), 0);
        lv_obj_set_style_text_font(lbl_stb_hint, &font_vietnamese_14, 0);
        lv_obj_align(lbl_stb_hint, LV_ALIGN_BOTTOM_MID, 0, -15);
    }

    void show_screensaver() {
        if (!modal_screensaver) return;
        screensaver_active = true;
        lv_obj_clear_flag(modal_screensaver, LV_OBJ_FLAG_HIDDEN);
        lv_obj_move_foreground(modal_screensaver);
    }

    void hide_screensaver() {
        if (!modal_screensaver) return;
        screensaver_active = false;
        lv_obj_add_flag(modal_screensaver, LV_OBJ_FLAG_HIDDEN);
    }

    bool is_screensaver_active() const {
        return screensaver_active;
    }

    void update_standby_clock(const char* time_str, const char* sec_str, const char* date_str, const char* clim_str = nullptr) {
        if (!modal_screensaver || !screensaver_active) return;
        if (lbl_stb_time && time_str) lv_label_set_text(lbl_stb_time, time_str);
        if (lbl_stb_sec && sec_str) lv_label_set_text(lbl_stb_sec, sec_str);
        if (lbl_stb_date && date_str) lv_label_set_text(lbl_stb_date, date_str);
        if (lbl_stb_clim && clim_str) lv_label_set_text(lbl_stb_clim, clim_str);
    }'''

code_norm = code.replace('\r\n', '\n')
for t, r, name in [
    (target_members, repl_members, 'members'),
    (target_ctor, repl_ctor, 'ctor'),
    (target_init_call, repl_init_call, 'init_call'),
    (target_event, repl_event, 'event'),
    (target_methods, repl_methods, 'methods')
]:
    t_n = t.replace('\r\n', '\n')
    r_n = r.replace('\r\n', '\n')
    if t_n in code_norm:
        code_norm = code_norm.replace(t_n, r_n, 1)
        print(f"SUCCESS: Patched ui_lvgl_dashboard.h ({name})")
    else:
        print(f"ERROR: Target not found ({name})")

with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(code_norm)

# 2. Update main.cpp
with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    main_code = f.read()

# Add ESP32Time include and rtc instance
target_main_inc = '''#include "ota_manager.h"
#include "esp_ota_ops.h"'''

repl_main_inc = '''#include "ota_manager.h"
#include "esp_ota_ops.h"
#include <ESP32Time.h>
ESP32Time rtc(7 * 3600); // Múi giờ Việt Nam GMT+7 (offset 25200s)'''

# Add time sync on ws text and NTP on connect
target_main_sync = '''    Serial.printf("[WS-TEXT] Handling type: %s, FreeHeap: %lu\\n", type.c_str(), (unsigned long)ESP.getFreeHeap());'''

repl_main_sync = '''    // Đồng bộ thời gian thực từ NAS Hub
    if (doc.containsKey("epoch") || doc.containsKey("timestamp")) {
        unsigned long ep = doc["epoch"] | doc["timestamp"] | 0;
        if (ep > 100000000) {
            rtc.setTime(ep);
            Serial.printf("[RTC] Dong bo gio tu NAS Hub thanh cong: %s\\n", rtc.getTime("%H:%M:%S").c_str());
        }
    }

    Serial.printf("[WS-TEXT] Handling type: %s, FreeHeap: %lu\\n", type.c_str(), (unsigned long)ESP.getFreeHeap());'''

# Add screensaver logic to Task_LVGL_UI
target_main_task = '''        if (!is_ota_running) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                uiDashboard.check_flush_climate_setpoint();
                uiDashboard.tick_countdown(millis());
                lv_timer_handler();
                xSemaphoreGive(lvgl_mutex);
            }
        }'''

repl_main_task = '''        if (!is_ota_running) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                uiDashboard.check_flush_climate_setpoint();
                uiDashboard.tick_countdown(millis());

                // Màn hình chờ Standby: Tự động vào sau 30 giây không thao tác
                uint32_t inactive_ms = lv_disp_get_inactive_time(NULL);
                if (!uiDashboard.is_screensaver_active() && inactive_ms >= 30000) {
                    uiDashboard.show_screensaver();
                } else if (uiDashboard.is_screensaver_active() && inactive_ms < 500) {
                    uiDashboard.hide_screensaver();
                }

                // Cập nhật đồng hồ mỗi giây khi màn hình chờ đang hiển thị
                static unsigned long last_stb_sec = 0;
                if (millis() - last_stb_sec >= 1000) {
                    last_stb_sec = millis();
                    if (uiDashboard.is_screensaver_active()) {
                        String time_str = rtc.getTime("%H:%M");
                        String sec_str = rtc.getTime(":%S");
                        int wday = rtc.getDayofWeek();
                        const char* wday_names[7] = {"Chủ Nhật", "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy"};
                        const char* wday_name = (wday >= 0 && wday < 7) ? wday_names[wday] : "Hôm nay";
                        String date_str = String(wday_name) + ", " + rtc.getTime("%d/%m/%Y");
                        uiDashboard.update_standby_clock(time_str.c_str(), sec_str.c_str(), date_str.c_str());
                    }
                }

                lv_timer_handler();
                xSemaphoreGive(lvgl_mutex);
            }
        }'''

main_norm = main_code.replace('\r\n', '\n')
for t, r, name in [
    (target_main_inc, repl_main_inc, 'main_inc'),
    (target_main_sync, repl_main_sync, 'main_sync'),
    (target_main_task, repl_main_task, 'main_task')
]:
    t_n = t.replace('\r\n', '\n')
    r_n = r.replace('\r\n', '\n')
    if t_n in main_norm:
        main_norm = main_norm.replace(t_n, r_n, 1)
        print(f"SUCCESS: Patched main.cpp ({name})")
    else:
        print(f"ERROR: Target not found ({name})")

with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(main_norm)
