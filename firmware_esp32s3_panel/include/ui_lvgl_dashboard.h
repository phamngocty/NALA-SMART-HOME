#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - LVGL 8.3.11 DASHBOARD (4 INDEPENDENT TABS)
 * - 100% Vietnamese Font (Tahoma 14 & 16) with all diacritics
 * - Tab 0: THIET BI (2-Column Scrollable Grid, 16 Buttons, Room Filter Chips, Master Off)
 * - Tab 1: NALA AI (AI Pulse Orb, Large Conversation Textarea, Big PTT Capsule)
 * - Tab 2: DAM THOAI (Intercom PCM 520B, Room Selection, All Call, PTT)
 * - Tab 3: CAI DAT (Volume, Brightness, Mic Gain, Diag Buttons, OTA, Ring Toggle)
 * - Full Tessera Climate Control Modal Dialog
 * ==============================================================================
 */

#include <Arduino.h>
#include <lvgl.h>
#include <ArduinoJson.h>
#include "font_vietnamese.h"

#define MAX_DASHBOARD_BUTTONS 16
#define MAX_ROOM_CHIPS 6

typedef void (*UIActionCallback_t)(const char* target, const char* action, int value);

struct UIButtonSlot {
    lv_obj_t* btn_obj = nullptr;
    lv_obj_t* lbl_obj = nullptr;
    String id;
    String name;
    String entity_id;
    String icon = "light";
    String room = "";
    bool is_on = false;
    float temperature = 26.0f;
    float current_temperature = 28.0f;
    String hvac_mode = "off";
    String fan_mode = "auto";
    bool swing_on = false;
};

class UILVGLDashboard {
private:
    lv_obj_t* tabview;
    lv_obj_t* tab_devices;
    lv_obj_t* tab_ai;
    lv_obj_t* tab_intercom;
    lv_obj_t* tab_settings;

    // Header Info (Top 38px)
    lv_obj_t* header_obj;
    lv_obj_t* lbl_header_title;
    lv_obj_t* lbl_header_info;
    lv_obj_t* lbl_ws_status;

    // Tab 0 Elements: Thiết Bị
    UIButtonSlot buttons[MAX_DASHBOARD_BUTTONS];
    uint8_t active_buttons_count;

    // Room Filter Chips Bar
    lv_obj_t* cont_room_chips;
    lv_obj_t* chip_all;
    lv_obj_t* lbl_chip_all;
    lv_obj_t* chip_rooms[MAX_ROOM_CHIPS];
    lv_obj_t* lbl_chip_rooms[MAX_ROOM_CHIPS];
    char chip_room_names[MAX_ROOM_CHIPS][24];
    uint8_t active_room_chips_count;
    String current_room_filter;

    // Summary Strip & Master Off
    lv_obj_t* strip_house_alert;
    lv_obj_t* lbl_house_alert;
    lv_obj_t* btn_master_off;
    lv_obj_t* lbl_master_off;

    // 2-Column Scrollable Grid
    lv_obj_t* cont_devices_scroll;

    // Tab 1 Elements: Nala AI
    lv_obj_t* lbl_ai_state;
    lv_obj_t* ai_pulse_circle;
    lv_obj_t* ta_ai_response;
    lv_obj_t* btn_ai_ptt;
    lv_obj_t* lbl_ai_ptt_text;

    // Tab 2 Elements: Đàm Thoại
    struct IntercomTarget {
        uint8_t id = 0;
        char name[28] = {0};
        char floor[16] = {0};
        bool is_online = false;
    };
    IntercomTarget intercom_targets[6];
    uint8_t active_intercom_targets_count;

    lv_obj_t* btn_rooms[4];
    lv_obj_t* lbl_rooms[4];
    lv_obj_t* btn_broadcast;
    lv_obj_t* btn_intercom_ptt;
    lv_obj_t* lbl_intercom_ptt;
    lv_obj_t* lbl_intercom_status;
    int selected_room_idx;

    // Tab 3 Elements: Cài Đặt
    lv_obj_t* slider_vol;
    lv_obj_t* lbl_vol_val;
    lv_obj_t* slider_bright;
    lv_obj_t* lbl_bright_val;
    lv_obj_t* slider_mic;
    lv_obj_t* lbl_mic_val;
    lv_obj_t* btn_enter_ap;
    lv_obj_t* btn_test_speaker;
    lv_obj_t* btn_test_mic;
    lv_obj_t* btn_test_ws;
    lv_obj_t* btn_check_ota;
    lv_obj_t* btn_toggle_ring;
    lv_obj_t* lbl_toggle_ring;
    bool ring_on_call_enabled;
    lv_obj_t* lbl_firmware_ver;
    lv_obj_t* lbl_diag_result;
    lv_obj_t* lbl_net_info;

    // Incoming Call Modal
    lv_obj_t* modal_incoming_call;
    lv_obj_t* lbl_incoming_title;
    lv_obj_t* lbl_incoming_caller;
    lv_obj_t* lbl_incoming_status;

    // Climate Dialog Modal (Tessera Glass)
    lv_obj_t* dialog_climate;
    lv_obj_t* lbl_clim_title;
    lv_obj_t* btn_clim_close;
    lv_obj_t* lbl_clim_temp;
    lv_obj_t* lbl_clim_status;
    lv_obj_t* btn_clim_minus;
    lv_obj_t* btn_clim_plus;
    lv_obj_t* btn_clim_modes[4];
    lv_obj_t* lbl_clim_modes[4];
    lv_obj_t* btn_clim_power;
    lv_obj_t* lbl_clim_power;
    lv_obj_t* btn_clim_fan;
    lv_obj_t* lbl_clim_fan;
    lv_obj_t* btn_clim_eco26;
    lv_obj_t* btn_clim_swing;
    lv_obj_t* lbl_clim_swing;
    lv_obj_t* lbl_clim_info;
    int active_climate_idx;

    // Debounce & Echo Lock
    bool climate_setpoint_pending;
    unsigned long climate_setpoint_tap_ms;
    unsigned long climate_echo_lock_until;

    UIActionCallback_t action_cb;

    static void event_handler_trampoline(lv_event_t* e) {
        UILVGLDashboard* instance = (UILVGLDashboard*)lv_event_get_user_data(e);
        if (instance) instance->handle_event(e);
    }

public:
    UILVGLDashboard()
        : tabview(nullptr), tab_devices(nullptr), tab_ai(nullptr), tab_intercom(nullptr), tab_settings(nullptr),
          header_obj(nullptr), lbl_header_title(nullptr), lbl_header_info(nullptr), lbl_ws_status(nullptr),
          active_buttons_count(0),
          cont_room_chips(nullptr), chip_all(nullptr), lbl_chip_all(nullptr),
          active_room_chips_count(0), current_room_filter("ALL"),
          strip_house_alert(nullptr), lbl_house_alert(nullptr), btn_master_off(nullptr), lbl_master_off(nullptr),
          cont_devices_scroll(nullptr),
          lbl_ai_state(nullptr), ai_pulse_circle(nullptr), ta_ai_response(nullptr), btn_ai_ptt(nullptr), lbl_ai_ptt_text(nullptr),
          active_intercom_targets_count(0),
          btn_broadcast(nullptr), btn_intercom_ptt(nullptr), lbl_intercom_ptt(nullptr),
          lbl_intercom_status(nullptr), selected_room_idx(0xFF),
          slider_vol(nullptr), lbl_vol_val(nullptr), slider_bright(nullptr), lbl_bright_val(nullptr),
          slider_mic(nullptr), lbl_mic_val(nullptr),
          btn_enter_ap(nullptr), btn_test_speaker(nullptr), btn_test_mic(nullptr), btn_test_ws(nullptr),
          btn_check_ota(nullptr), btn_toggle_ring(nullptr), lbl_toggle_ring(nullptr),
          ring_on_call_enabled(true), lbl_firmware_ver(nullptr),
          lbl_diag_result(nullptr), lbl_net_info(nullptr),
          modal_incoming_call(nullptr), lbl_incoming_title(nullptr),
          lbl_incoming_caller(nullptr), lbl_incoming_status(nullptr),
          dialog_climate(nullptr), lbl_clim_title(nullptr), btn_clim_close(nullptr),
          lbl_clim_temp(nullptr), lbl_clim_status(nullptr),
          btn_clim_minus(nullptr), btn_clim_plus(nullptr),
          btn_clim_power(nullptr), lbl_clim_power(nullptr),
          btn_clim_fan(nullptr), lbl_clim_fan(nullptr),
          btn_clim_eco26(nullptr), btn_clim_swing(nullptr), lbl_clim_swing(nullptr),
          lbl_clim_info(nullptr), active_climate_idx(-1),
          climate_setpoint_pending(false), climate_setpoint_tap_ms(0), climate_echo_lock_until(0),
          action_cb(nullptr) {

        for (int m = 0; m < 4; m++) {
            btn_clim_modes[m] = nullptr;
            lbl_clim_modes[m] = nullptr;
        }
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            chip_rooms[i] = nullptr;
            lbl_chip_rooms[i] = nullptr;
            chip_room_names[i][0] = '\0';
        }
        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = nullptr;
            lbl_rooms[i] = nullptr;
        }
        for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
            buttons[i].btn_obj = nullptr;
            buttons[i].lbl_obj = nullptr;
            buttons[i].is_on = false;
            buttons[i].name = "";
            buttons[i].entity_id = "";
            buttons[i].icon = "light";
            buttons[i].room = "";
        }
    }

    void set_action_callback(UIActionCallback_t cb) {
        action_cb = cb;
    }

    void check_flush_climate_setpoint() {
        if (climate_setpoint_pending && (millis() - climate_setpoint_tap_ms >= 450)) {
            climate_setpoint_pending = false;
            climate_echo_lock_until = millis() + 3000;
            if (action_cb && active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                action_cb("climate_temp", b.entity_id.c_str(), (int)(b.temperature * 10));
            }
        }
    }

    void init(const char* room_name, const char* ip_str, const char* pair_code, 
              uint8_t init_vol, uint8_t init_bright, bool init_ring_on_call = true, uint8_t init_mic_gain = 5) {
        ring_on_call_enabled = init_ring_on_call;
        lv_obj_t* scr = lv_scr_act();
        lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(scr, lv_color_hex(0x080C14), 0); // Apple Deep Dark

        // Header trên cùng (Cao 38px, rộng 240px)
        header_obj = lv_obj_create(scr);
        lv_obj_set_size(header_obj, 240, 38);
        lv_obj_align(header_obj, LV_ALIGN_TOP_MID, 0, 0);
        lv_obj_set_style_bg_color(header_obj, lv_color_hex(0x0D1527), 0);
        lv_obj_set_style_border_side(header_obj, LV_BORDER_SIDE_BOTTOM, 0);
        lv_obj_set_style_border_color(header_obj, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_width(header_obj, 1, 0);
        lv_obj_set_style_pad_all(header_obj, 2, 0);
        lv_obj_clear_flag(header_obj, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(header_obj, event_handler_trampoline, LV_EVENT_LONG_PRESSED, this);

        lbl_header_title = lv_label_create(header_obj);
        lv_label_set_text_fmt(lbl_header_title, "NALA: %s", room_name && strlen(room_name) > 0 ? room_name : "Thiết Bị");
        lv_obj_set_style_text_color(lbl_header_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_header_title, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_title, LV_ALIGN_TOP_LEFT, 4, -1);

        lbl_ws_status = lv_label_create(header_obj);
        lv_label_set_text(lbl_ws_status, "Offline");
        lv_obj_set_style_text_color(lbl_ws_status, lv_color_hex(0xEF4444), 0);
        lv_obj_set_style_text_font(lbl_ws_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_ws_status, LV_ALIGN_TOP_RIGHT, -4, -1);

        lbl_header_info = lv_label_create(header_obj);
        lv_label_set_text_fmt(lbl_header_info, "IP: %s | Mã: [%s]", ip_str ? ip_str : "192.168.1.x", pair_code ? pair_code : "881C");
        lv_obj_set_style_text_color(lbl_header_info, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_header_info, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_info, LV_ALIGN_BOTTOM_LEFT, 4, 1);

        // TabView (Dưới Header, Cao 282px, Rộng 240px, 4 Tab đáy)
        tabview = lv_tabview_create(scr, LV_DIR_BOTTOM, 36);
        lv_obj_set_size(tabview, 240, 282);
        lv_obj_align(tabview, LV_ALIGN_BOTTOM_MID, 0, 0);
        lv_obj_set_style_bg_color(tabview, lv_color_hex(0x080C14), 0);

        lv_obj_t* tab_btns = lv_tabview_get_tab_btns(tabview);
        lv_obj_set_style_bg_color(tab_btns, lv_color_hex(0x0F172A), 0);
        lv_obj_set_style_text_color(tab_btns, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(tab_btns, &font_vietnamese_14, 0);
        lv_obj_clear_flag(lv_tabview_get_content(tabview), LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(tab_btns, event_handler_trampoline, LV_EVENT_ALL, this);
        lv_obj_add_event_cb(tabview, event_handler_trampoline, LV_EVENT_ALL, this);

        // 4 Tab độc lập: Thiết Bị | Nala AI | Đàm Thoại | Cài Đặt
        tab_devices = lv_tabview_add_tab(tabview, "Thiết Bị");
        tab_ai = lv_tabview_add_tab(tabview, "Nala AI");
        tab_intercom = lv_tabview_add_tab(tabview, "Đàm Thoại");
        tab_settings = lv_tabview_add_tab(tabview, "Cài Đặt");

        build_tab_devices();
        build_tab_ai();
        build_tab_intercom();
        build_tab_settings(init_vol, init_bright, init_mic_gain);

        build_incoming_call_modal(scr);
        build_climate_dialog(scr);
    }

    void set_ws_connected(bool connected) {
        if (lbl_ws_status) {
            if (connected) {
                lv_label_set_text(lbl_ws_status, "Online");
                lv_obj_set_style_text_color(lbl_ws_status, lv_color_hex(0x10B981), 0);
            } else {
                lv_label_set_text(lbl_ws_status, "Offline");
                lv_obj_set_style_text_color(lbl_ws_status, lv_color_hex(0xEF4444), 0);
            }
        }
    }

    void set_firmware_version(const char* ver_str, float psram_mb = 0.0f) {
        if (lbl_firmware_ver && ver_str) {
            char buf[64];
            snprintf(buf, sizeof(buf), "Bản: %s | PSRAM: %.1fMB", ver_str, psram_mb);
            lv_label_set_text(lbl_firmware_ver, buf);
        }
    }

    void set_diag_result(const char* text, uint32_t color_hex) {
        if (lbl_diag_result && text) {
            lv_label_set_text(lbl_diag_result, text);
            lv_obj_set_style_text_color(lbl_diag_result, lv_color_hex(color_hex), 0);
        }
    }

    void sync_buttons(const JsonArrayConst& btn_array) {
        uint8_t count = btn_array.size();
        if (count > MAX_DASHBOARD_BUTTONS) count = MAX_DASHBOARD_BUTTONS;
        active_buttons_count = count;

        for (uint8_t i = 0; i < count; i++) {
            buttons[i].id = btn_array[i]["id"] | String("btn_" + String(i + 1));
            buttons[i].name = btn_array[i]["name"] | String("Nút " + String(i + 1));
            buttons[i].entity_id = btn_array[i]["entity_id"] | "";
            buttons[i].icon = btn_array[i]["icon"] | "light";
            buttons[i].room = btn_array[i]["room"] | "";

            bool is_on = btn_array[i]["is_on"] | false;
            if (!is_on && btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                is_on = (st == "on" || (st != "off" && st != "unavailable" && st != "unknown" && st.length() > 0));
            }
            buttons[i].is_on = is_on;

            if (btn_array[i].containsKey("attributes")) {
                JsonObjectConst attrs = btn_array[i]["attributes"];
                if (attrs.containsKey("temperature")) {
                    buttons[i].temperature = attrs["temperature"] | 26.0f;
                }
                if (attrs.containsKey("current_temperature")) {
                    buttons[i].current_temperature = attrs["current_temperature"] | 28.0f;
                }
                if (attrs.containsKey("hvac_mode")) {
                    buttons[i].hvac_mode = attrs["hvac_mode"] | "off";
                }
                if (attrs.containsKey("fan_mode")) {
                    buttons[i].fan_mode = attrs["fan_mode"] | "auto";
                }
                if (attrs.containsKey("swing_mode")) {
                    String sm = attrs["swing_mode"] | "";
                    buttons[i].swing_on = (sm != "off" && sm.length() > 0);
                }
            }
            if (btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                buttons[i].hvac_mode = st;
            }
        }

        filter_devices_by_room(current_room_filter);
    }

    void sync_house_status(const JsonObjectConst& house_st) {
        if (!lbl_house_alert) return;
        int on_lights = house_st["total_on_lights"] | 0;
        int on_fans = house_st["total_on_fans"] | 0;
        const char* summary = house_st["summary_text"] | "";
        if (summary && strlen(summary) > 0) {
            lv_label_set_text(lbl_house_alert, summary);
        } else if (on_lights > 0 || on_fans > 0) {
            char buf[64];
            snprintf(buf, sizeof(buf), "%d ĐÈN & %d QUẠT BẬT", on_lights, on_fans);
            lv_label_set_text(lbl_house_alert, buf);
        } else {
            lv_label_set_text(lbl_house_alert, "ĐÃ TẮT HẾT CÁC PHÒNG");
        }

        if (on_lights > 0 || on_fans > 0) {
            lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0xF59E0B), 0);
            if (btn_master_off) lv_obj_clear_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0x10B981), 0);
            if (btn_master_off) lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
        }
    }

    void sync_all_rooms(const JsonArrayConst& rooms_array) {
        active_room_chips_count = 0;
        for (JsonObjectConst r : rooms_array) {
            if (active_room_chips_count >= MAX_ROOM_CHIPS) break;
            const char* rname = r["room_name"] | "";
            if (rname && strlen(rname) > 0) {
                strncpy(chip_room_names[active_room_chips_count], rname, sizeof(chip_room_names[0]) - 1);
                chip_room_names[active_room_chips_count][sizeof(chip_room_names[0]) - 1] = '\0';
                active_room_chips_count++;
            }
        }
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            if (!chip_rooms[i]) continue;
            if (i < active_room_chips_count) {
                lv_obj_clear_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
                if (lbl_chip_rooms[i]) {
                    lv_label_set_text(lbl_chip_rooms[i], chip_room_names[i]);
                }
            } else {
                lv_obj_add_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    void filter_devices_by_room(const String& room) {
        current_room_filter = room;

        // Cập nhật trạng thái màu cho các chip lọc
        bool is_all = (room.equalsIgnoreCase("ALL") || room == "");
        if (chip_all) {
            if (is_all) {
                lv_obj_set_style_bg_color(chip_all, lv_color_hex(0x0284C7), 0);
                lv_obj_set_style_border_color(chip_all, lv_color_hex(0x38BDF8), 0);
            } else {
                lv_obj_set_style_bg_color(chip_all, lv_color_hex(0x111927), 0);
                lv_obj_set_style_border_color(chip_all, lv_color_hex(0x27354A), 0);
            }
        }
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            if (!chip_rooms[i]) continue;
            if (!is_all && room.equalsIgnoreCase(chip_room_names[i])) {
                lv_obj_set_style_bg_color(chip_rooms[i], lv_color_hex(0x0284C7), 0);
                lv_obj_set_style_border_color(chip_rooms[i], lv_color_hex(0x38BDF8), 0);
            } else {
                lv_obj_set_style_bg_color(chip_rooms[i], lv_color_hex(0x111927), 0);
                lv_obj_set_style_border_color(chip_rooms[i], lv_color_hex(0x27354A), 0);
            }
        }

        // Bố trí lại vị trí các nút thỏa mãn điều kiện lọc
        int visible_idx = 0;
        for (int i = 0; i < active_buttons_count; i++) {
            if (!buttons[i].btn_obj) continue;
            bool match = (is_all || buttons[i].room.equalsIgnoreCase(room) || buttons[i].room == "");
            if (match) {
                lv_obj_clear_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                int x = (visible_idx % 2 == 0) ? 0 : 116;
                int y = (visible_idx / 2) * 50;
                lv_obj_set_pos(buttons[i].btn_obj, x, y);
                update_button_ui(i);
                visible_idx++;
            } else {
                lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
        }
        for (int i = active_buttons_count; i < MAX_DASHBOARD_BUTTONS; i++) {
            if (buttons[i].btn_obj) {
                lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    void update_entity_state(const char* entity_id, bool is_on, float temp = 0.0f,
                             float current_temp = 0.0f, const char* mode = nullptr,
                             const char* fan = nullptr, int swing = -1) {
        for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
            if (buttons[i].entity_id.equalsIgnoreCase(entity_id)) {
                buttons[i].is_on = is_on;

                if (temp > 10.0f) {
                    if (millis() >= climate_echo_lock_until) {
                        buttons[i].temperature = temp;
                    }
                }
                if (current_temp > 10.0f) {
                    buttons[i].current_temperature = current_temp;
                }
                if (mode && strlen(mode) > 0) {
                    buttons[i].hvac_mode = mode;
                }
                if (fan && strlen(fan) > 0) {
                    buttons[i].fan_mode = fan;
                }
                if (swing >= 0) {
                    buttons[i].swing_on = (swing > 0);
                }

                update_button_ui(i);
                if (dialog_climate && !lv_obj_has_flag(dialog_climate, LV_OBJ_FLAG_HIDDEN) && active_climate_idx == i) {
                    update_climate_dialog_ui();
                }
            }
        }
    }

    void set_room_title(const char* room_name) {
        if (lbl_header_title && room_name) {
            lv_label_set_text_fmt(lbl_header_title, "NALA: %s", room_name);
        }
    }

    void set_ai_state(const char* state_str, const char* text = nullptr) {
        if (lbl_ai_state && state_str) {
            if (strcasecmp(state_str, "listening") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang nghe...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
                if (ai_pulse_circle) lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0284C7), 0);
            } else if (strcasecmp(state_str, "processing") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang suy nghĩ...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0xF59E0B), 0);
                if (ai_pulse_circle) lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0xD97706), 0);
            } else if (strcasecmp(state_str, "speaking") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang trả lời...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
                if (ai_pulse_circle) lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x059669), 0);
            } else {
                lv_label_set_text(lbl_ai_state, "AI: Sẵn sàng (Chờ lệnh)");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
                if (ai_pulse_circle) lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x1E293B), 0);
            }
        }
        if (text && strlen(text) > 0) {
            set_ai_text(text);
        }
    }

    void set_ai_text(const char* text_str) {
        if (ta_ai_response && text_str) {
            lv_textarea_set_text(ta_ai_response, text_str);
        }
    }

    void sync_intercom_targets(const JsonArrayConst& targets_array) {
        sync_intercom_targets(0, targets_array);
    }

    void sync_intercom_targets(uint8_t my_id, const JsonArrayConst& targets_array) {
        active_intercom_targets_count = 0;
        for (JsonObjectConst target : targets_array) {
            if (active_intercom_targets_count >= 4) break;
            uint8_t id = target["id"] | 0;
            if (id == my_id || id == 0) continue;

            intercom_targets[active_intercom_targets_count].id = id;
            const char* name = target["name"] | "Phòng";
            const char* fl = target["floor"] | "";
            strncpy(intercom_targets[active_intercom_targets_count].name, name, sizeof(intercom_targets[0].name) - 1);
            strncpy(intercom_targets[active_intercom_targets_count].floor, fl, sizeof(intercom_targets[0].floor) - 1);
            intercom_targets[active_intercom_targets_count].is_online = target["online"] | false;
            active_intercom_targets_count++;
        }

        for (int i = 0; i < 4; i++) {
            if (!btn_rooms[i] || !lbl_rooms[i]) continue;
            if (i < active_intercom_targets_count) {
                lv_obj_clear_flag(btn_rooms[i], LV_OBJ_FLAG_HIDDEN);
                lv_label_set_text(lbl_rooms[i], intercom_targets[i].name);
            } else {
                lv_obj_add_flag(btn_rooms[i], LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    void set_intercom_status(const char* text, uint32_t color_hex) {
        if (lbl_intercom_status && text) {
            lv_label_set_text(lbl_intercom_status, text);
            lv_obj_set_style_text_color(lbl_intercom_status, lv_color_hex(color_hex), 0);
        }
    }

    void get_caller_display(uint8_t sender_id, char* buf, size_t buf_len) {
        if (!buf || buf_len == 0) return;
        for (int i = 0; i < active_intercom_targets_count; i++) {
            if (intercom_targets[i].id == sender_id) {
                snprintf(buf, buf_len, "%s", intercom_targets[i].name);
                return;
            }
        }
        snprintf(buf, buf_len, "Thiết bị #%d", sender_id);
    }

    void show_incoming_call(const char* caller_name, bool ring) {
        if (!modal_incoming_call) return;
        if (lbl_incoming_caller && caller_name) {
            lv_label_set_text(lbl_incoming_caller, caller_name);
        }
        if (lbl_incoming_status) {
            if (ring) {
                lv_label_set_text(lbl_incoming_status, "Đang đổ chuông...");
                lv_obj_set_style_text_color(lbl_incoming_status, lv_color_hex(0xF59E0B), 0);
            } else {
                lv_label_set_text(lbl_incoming_status, "Đang đàm thoại trực tiếp...");
                lv_obj_set_style_text_color(lbl_incoming_status, lv_color_hex(0x10B981), 0);
            }
        }
        lv_obj_clear_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);
        lv_obj_move_foreground(modal_incoming_call);
    }

    void hide_incoming_call() {
        if (modal_incoming_call) {
            lv_obj_add_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);
        }
    }

    void sync_settings(uint8_t vol, uint8_t bright, bool ring, uint8_t mic_gain) {
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

    void update_ring_toggle_ui() {
        if (lbl_toggle_ring && btn_toggle_ring) {
            if (ring_on_call_enabled) {
                lv_label_set_text(lbl_toggle_ring, "CHUÔNG: BẬT");
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x0284C7), 0);
            } else {
                lv_label_set_text(lbl_toggle_ring, "CHUÔNG: TẮT");
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x334155), 0);
            }
        }
    }

private:
    void handle_event(lv_event_t* e) {
        lv_obj_t* target = lv_event_get_target(e);
        lv_event_code_t code = lv_event_get_code(e);

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
        }

        if (target == header_obj && code == LV_EVENT_LONG_PRESSED) {
            if (action_cb) action_cb("system", "enter_ap_mode", 0);
            return;
        }

        // Room filter chips
        if (target == chip_all && code == LV_EVENT_CLICKED) {
            Serial.println("[UI-ACTION] Clicked TOÀN NHÀ chip!");
            filter_devices_by_room("ALL");
            return;
        }
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            if (target == chip_rooms[i] && code == LV_EVENT_CLICKED) {
                filter_devices_by_room(chip_room_names[i]);
                return;
            }
        }

        // Master Turn Off All
        if (target == btn_master_off && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("master_turn_off_all", "", 0);
            return;
        }

        // Device buttons
        for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
            if (target == buttons[i].btn_obj && code == LV_EVENT_CLICKED) {
                Serial.printf("[UI-ACTION] Clicked Button %d (%s) entity=%s is_on=%d\n", 
                              i, buttons[i].name.c_str(), buttons[i].entity_id.c_str(), (int)buttons[i].is_on);
                bool is_climate = (buttons[i].icon == "climate" || buttons[i].entity_id.startsWith("climate"));
                if (is_climate) {
                    open_climate_dialog(i);
                } else if (buttons[i].entity_id.length() > 0 && action_cb) {
                    buttons[i].is_on = !buttons[i].is_on;
                    update_button_ui(i);
                    action_cb("entity_toggle", buttons[i].entity_id.c_str(), buttons[i].is_on);
                }
                return;
            }
        }

        // Climate Dialog Events
        if (target == btn_clim_close && code == LV_EVENT_CLICKED) {
            close_climate_dialog();
            return;
        }
        if (target == btn_clim_minus && code == LV_EVENT_CLICKED) {
            if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                if (b.temperature > 16.0f) {
                    b.temperature -= 0.5f;
                    climate_setpoint_pending = true;
                    climate_setpoint_tap_ms = millis();
                    update_climate_dialog_ui();
                }
            }
            return;
        }
        if (target == btn_clim_plus && code == LV_EVENT_CLICKED) {
            if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                if (b.temperature < 32.0f) {
                    b.temperature += 0.5f;
                    climate_setpoint_pending = true;
                    climate_setpoint_tap_ms = millis();
                    update_climate_dialog_ui();
                }
            }
            return;
        }
        for (int m = 0; m < 4; m++) {
            if (target == btn_clim_modes[m] && code == LV_EVENT_CLICKED) {
                if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                    UIButtonSlot& b = buttons[active_climate_idx];
                    const char* modes[] = {"cool", "fan_only", "dry", "auto"};
                    b.hvac_mode = modes[m];
                    b.is_on = true;
                    update_climate_dialog_ui();
                    update_button_ui(active_climate_idx);
                    if (action_cb) action_cb("climate_mode", b.entity_id.c_str(), m);
                }
                return;
            }
        }
        if (target == btn_clim_power && code == LV_EVENT_CLICKED) {
            if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                b.is_on = !b.is_on;
                b.hvac_mode = b.is_on ? "cool" : "off";
                update_climate_dialog_ui();
                update_button_ui(active_climate_idx);
                if (action_cb) action_cb("entity_toggle", b.entity_id.c_str(), b.is_on);
            }
            return;
        }
        if (target == btn_clim_fan && code == LV_EVENT_CLICKED) {
            if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                int cur_idx = 0;
                if (b.fan_mode == "low") cur_idx = 1;
                else if (b.fan_mode == "medium") cur_idx = 2;
                else if (b.fan_mode == "high") cur_idx = 3;
                int next_idx = (cur_idx + 1) % 4;
                const char* fan_modes[] = {"auto", "low", "medium", "high"};
                b.fan_mode = fan_modes[next_idx];
                update_climate_dialog_ui();
                if (action_cb) action_cb("climate_fan", b.entity_id.c_str(), next_idx);
            }
            return;
        }
        if (target == btn_clim_swing && code == LV_EVENT_CLICKED) {
            if (active_climate_idx >= 0 && active_climate_idx < MAX_DASHBOARD_BUTTONS) {
                UIButtonSlot& b = buttons[active_climate_idx];
                b.swing_on = !b.swing_on;
                update_climate_dialog_ui();
                if (action_cb) action_cb("climate_swing", b.entity_id.c_str(), b.swing_on ? 1 : 0);
            }
            return;
        }

        // Nút nói chuyện với AI (PTT)
        if (target == btn_ai_ptt) {
            if (code == LV_EVENT_PRESSED) {
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0xEF4444), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "ĐANG THU ÂM (NHẢ ĐỂ GỬI)");
                if (action_cb) action_cb("ptt_ai", "start", 1);
            } else if (code == LV_EVENT_RELEASED) {
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x0284C7), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "GIỮ ĐỂ NÓI VỚI NALA AI");
                if (action_cb) action_cb("ptt_ai", "stop", 0);
            }
            return;
        }

        // Intercom Target Rooms
        for (int i = 0; i < 4; i++) {
            if (target == btn_rooms[i] && code == LV_EVENT_CLICKED) {
                highlight_selected_room(i);
                return;
            }
        }
        if (target == btn_broadcast && code == LV_EVENT_CLICKED) {
            highlight_selected_room(-1);
            return;
        }

        // Intercom PTT
        if (target == btn_intercom_ptt) {
            if (code == LV_EVENT_PRESSED) {
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0xEF4444), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "ĐANG ĐÀM THOẠI...");
                set_intercom_status("Đang phát âm thanh...", 0xEF4444);
                if (action_cb) action_cb("ptt_intercom", "start", selected_room_idx);
            } else if (code == LV_EVENT_RELEASED) {
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x0284C7), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "NHẤN GIỮ ĐỂ NÓI");
                set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                if (action_cb) action_cb("ptt_intercom", "stop", selected_room_idx);
            }
            return;
        }

        // Sliders & Settings
        if (target == slider_vol && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_vol);
            if (lbl_vol_val) lv_label_set_text_fmt(lbl_vol_val, "%d%%", val);
            if (action_cb) action_cb("settings", "vol", val);
            return;
        }
        if (target == slider_bright && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_bright);
            if (lbl_bright_val) lv_label_set_text_fmt(lbl_bright_val, "%d", val);
            if (action_cb) action_cb("settings", "bright", val);
            return;
        }
        if (target == slider_mic && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_mic);
            if (lbl_mic_val) {
                const char* gain_names[8] = {"", "Thấp", "Vừa", "Chuẩn", "Nhạy", "Rất nhạy", "Cực nhạy", "Tối đa"};
                char m_buf[32];
                snprintf(m_buf, sizeof(m_buf), "Mức %d (%s)", val, (val >= 1 && val <= 7) ? gain_names[val] : "");
                lv_label_set_text(lbl_mic_val, m_buf);
            }
            if (action_cb) action_cb("settings_mic", "gain", val);
            return;
        }

        // Diag & Settings Buttons
        if (target == btn_test_speaker && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("diag", "speaker", 0);
            return;
        }
        if (target == btn_test_mic && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("diag", "mic", 0);
            return;
        }
        if (target == btn_toggle_ring && code == LV_EVENT_CLICKED) {
            ring_on_call_enabled = !ring_on_call_enabled;
            update_ring_toggle_ui();
            if (action_cb) action_cb("settings", "ring_call", ring_on_call_enabled ? 1 : 0);
            return;
        }
        if (target == btn_test_ws && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("diag", "ws_ping", 0);
            return;
        }
        if (target == btn_enter_ap && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("system", "enter_ap_mode", 0);
            return;
        }
        if (target == btn_check_ota && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("system", "check_ota", 0);
            return;
        }
    }

    void update_button_ui(int idx) {
        if (idx < 0 || idx >= MAX_DASHBOARD_BUTTONS) return;
        UIButtonSlot& b = buttons[idx];
        if (!b.btn_obj || !b.lbl_obj) return;

        bool is_climate = (b.icon == "climate" || b.entity_id.startsWith("climate"));
        String display_name = b.name;
        if (is_climate) {
            display_name = "Máy Lạnh";
        } else if (display_name.length() > 10) {
            display_name = display_name.substring(0, 10);
        }

        char btn_text[64];
        if (is_climate) {
            if (b.is_on && b.temperature > 10.0f) {
                snprintf(btn_text, sizeof(btn_text), "%s\n%.1f°C", display_name.c_str(), b.temperature);
            } else {
                snprintf(btn_text, sizeof(btn_text), "%s\nTẮT", display_name.c_str());
            }
        } else {
            const char* st_text = b.is_on ? "BẬT" : "TẮT";
            snprintf(btn_text, sizeof(btn_text), "%s\n%s", display_name.c_str(), st_text);
        }
        lv_label_set_text(b.lbl_obj, btn_text);
        lv_obj_set_style_text_align(b.lbl_obj, LV_TEXT_ALIGN_CENTER, 0);

        if (b.is_on) {
            if (is_climate) {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x0C3826), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x10B981), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            } else if (b.icon == "fan" || b.entity_id.startsWith("fan")) {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x0C3345), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x38BDF8), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            } else {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x1E3A8A), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x38BDF8), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            }
        } else {
            lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x111927), 0);
            lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x27354A), 0);
            lv_obj_set_style_border_width(b.btn_obj, 1, 0);
            lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0x94A3B8), 0);
        }
    }

    void highlight_selected_room(int idx) {
        for (int i = 0; i < 4; i++) {
            if (btn_rooms[i]) {
                if (i == idx) {
                    lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x0284C7), 0);
                    lv_obj_set_style_border_color(btn_rooms[i], lv_color_hex(0x38BDF8), 0);
                } else {
                    lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x111927), 0);
                    lv_obj_set_style_border_color(btn_rooms[i], lv_color_hex(0x27354A), 0);
                }
            }
        }
        if (btn_broadcast) {
            if (idx == -1) {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0xD97706), 0);
                lv_obj_set_style_border_color(btn_broadcast, lv_color_hex(0xFBBF24), 0);
            } else {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x111927), 0);
                lv_obj_set_style_border_color(btn_broadcast, lv_color_hex(0x27354A), 0);
            }
        }
        selected_room_idx = (idx == -1) ? 0xFF : ((idx >= 0 && idx < active_intercom_targets_count) ? intercom_targets[idx].id : 0xFF);
    }

    void build_tab_devices() {
        lv_obj_clear_flag(tab_devices, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_devices, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_devices, 2, 0);

        // 1. Room Filter Bar (Horizontal scroll) - Y: 2, H: 26
        cont_room_chips = lv_obj_create(tab_devices);
        lv_obj_set_size(cont_room_chips, 236, 28);
        lv_obj_set_pos(cont_room_chips, 2, 2);
        lv_obj_set_style_bg_opa(cont_room_chips, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(cont_room_chips, 0, 0);
        lv_obj_set_style_pad_all(cont_room_chips, 0, 0);
        lv_obj_set_scroll_dir(cont_room_chips, LV_DIR_HOR);
        lv_obj_set_scrollbar_mode(cont_room_chips, LV_SCROLLBAR_MODE_OFF);

        // Chip "TOÀN NHÀ"
        chip_all = lv_btn_create(cont_room_chips);
        lv_obj_set_size(chip_all, 74, 24);
        lv_obj_set_pos(chip_all, 0, 2);
        lv_obj_set_style_radius(chip_all, 12, 0);
        lv_obj_set_style_bg_color(chip_all, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_border_color(chip_all, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(chip_all, 1, 0);
        lv_obj_set_style_pad_all(chip_all, 1, 0);
        lv_obj_add_event_cb(chip_all, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_chip_all = lv_label_create(chip_all);
        lv_obj_clear_flag(lbl_chip_all, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_chip_all, "TOÀN NHÀ");
        lv_obj_set_style_text_font(lbl_chip_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_chip_all);

        int chip_x = 78;
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            chip_rooms[i] = lv_btn_create(cont_room_chips);
            lv_obj_set_size(chip_rooms[i], 76, 24);
            lv_obj_set_pos(chip_rooms[i], chip_x, 2);
            lv_obj_set_style_radius(chip_rooms[i], 12, 0);
            lv_obj_set_style_bg_color(chip_rooms[i], lv_color_hex(0x111927), 0);
            lv_obj_set_style_border_color(chip_rooms[i], lv_color_hex(0x27354A), 0);
            lv_obj_set_style_border_width(chip_rooms[i], 1, 0);
            lv_obj_set_style_pad_all(chip_rooms[i], 1, 0);
            lv_obj_add_event_cb(chip_rooms[i], event_handler_trampoline, LV_EVENT_CLICKED, this);

            lbl_chip_rooms[i] = lv_label_create(chip_rooms[i]);
            lv_obj_clear_flag(lbl_chip_rooms[i], LV_OBJ_FLAG_CLICKABLE);
            lv_label_set_text(lbl_chip_rooms[i], "");
            lv_obj_set_style_text_font(lbl_chip_rooms[i], &font_vietnamese_14, 0);
            lv_obj_center(lbl_chip_rooms[i]);
            lv_obj_add_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
            chip_x += 80;
        }

        // 2. Summary Status Bar (Amber/Crimson alert) - Y: 32, H: 26
        strip_house_alert = lv_obj_create(tab_devices);
        lv_obj_set_size(strip_house_alert, 236, 26);
        lv_obj_set_pos(strip_house_alert, 2, 32);
        lv_obj_set_style_bg_color(strip_house_alert, lv_color_hex(0x1C1917), 0);
        lv_obj_set_style_border_color(strip_house_alert, lv_color_hex(0x78350F), 0);
        lv_obj_set_style_border_width(strip_house_alert, 1, 0);
        lv_obj_set_style_radius(strip_house_alert, 6, 0);
        lv_obj_set_style_pad_all(strip_house_alert, 2, 0);

        lbl_house_alert = lv_label_create(strip_house_alert);
        lv_label_set_text(lbl_house_alert, "Tất cả thiết bị tắt");
        lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_house_alert, &font_vietnamese_14, 0);
        lv_obj_align(lbl_house_alert, LV_ALIGN_LEFT_MID, 4, 0);

        btn_master_off = lv_btn_create(strip_house_alert);
        lv_obj_set_size(btn_master_off, 68, 20);
        lv_obj_align(btn_master_off, LV_ALIGN_RIGHT_MID, -2, 0);
        lv_obj_set_style_bg_color(btn_master_off, lv_color_hex(0xDC2626), 0);
        lv_obj_set_style_radius(btn_master_off, 4, 0);
        lv_obj_set_style_pad_all(btn_master_off, 0, 0);
        lv_obj_add_event_cb(btn_master_off, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_master_off = lv_label_create(btn_master_off);
        lv_obj_clear_flag(lbl_master_off, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_master_off, "TẮT HẾT");
        lv_obj_set_style_text_font(lbl_master_off, &font_vietnamese_14, 0);
        lv_obj_center(lbl_master_off);
        lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);

        // 3. Scrollable 2-Column Device Grid - Y: 60, H: 178
        cont_devices_scroll = lv_obj_create(tab_devices);
        lv_obj_set_size(cont_devices_scroll, 236, 178);
        lv_obj_set_pos(cont_devices_scroll, 2, 60);
        lv_obj_set_style_bg_opa(cont_devices_scroll, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(cont_devices_scroll, 0, 0);
        lv_obj_set_style_pad_all(cont_devices_scroll, 0, 0);
        lv_obj_set_scroll_dir(cont_devices_scroll, LV_DIR_VER);
        lv_obj_set_scrollbar_mode(cont_devices_scroll, LV_SCROLLBAR_MODE_AUTO);

        for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
            buttons[i].btn_obj = lv_btn_create(cont_devices_scroll);
            lv_obj_set_size(buttons[i].btn_obj, 112, 44);
            int x = (i % 2 == 0) ? 0 : 116;
            int y = (i / 2) * 50;
            lv_obj_set_pos(buttons[i].btn_obj, x, y);
            lv_obj_set_style_radius(buttons[i].btn_obj, 10, 0);
            lv_obj_set_style_border_width(buttons[i].btn_obj, 1, 0);
            lv_obj_set_style_pad_all(buttons[i].btn_obj, 2, 0);
            lv_obj_add_event_cb(buttons[i].btn_obj, event_handler_trampoline, LV_EVENT_CLICKED, this);

            buttons[i].lbl_obj = lv_label_create(buttons[i].btn_obj);
            lv_obj_clear_flag(buttons[i].lbl_obj, LV_OBJ_FLAG_CLICKABLE);
            lv_obj_set_style_text_font(buttons[i].lbl_obj, &font_vietnamese_14, 0);
            lv_obj_center(buttons[i].lbl_obj);

            if (i >= active_buttons_count) {
                lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            } else {
                update_button_ui(i);
            }
        }
    }

    void build_tab_ai() {
        lv_obj_clear_flag(tab_ai, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_ai, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_ai, 6, 0);

        // Header: AI Status & Pulse Indicator
        lbl_ai_state = lv_label_create(tab_ai);
        lv_label_set_text(lbl_ai_state, "AI: Sẵn sàng (Chờ lệnh)");
        lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_ai_state, &font_vietnamese_14, 0);
        lv_obj_align(lbl_ai_state, LV_ALIGN_TOP_MID, 0, 4);

        // Visual AI Orb / Waveform container
        ai_pulse_circle = lv_obj_create(tab_ai);
        lv_obj_set_size(ai_pulse_circle, 44, 44);
        lv_obj_align(ai_pulse_circle, LV_ALIGN_TOP_MID, 0, 24);
        lv_obj_set_style_radius(ai_pulse_circle, LV_RADIUS_CIRCLE, 0);
        lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0369A1), 0);
        lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(ai_pulse_circle, 2, 0);

        lv_obj_t* lbl_orb = lv_label_create(ai_pulse_circle);
        lv_label_set_text(lbl_orb, "NALA");
        lv_obj_set_style_text_font(lbl_orb, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_orb, lv_color_hex(0xFFFFFF), 0);
        lv_obj_center(lbl_orb);

        // Large Text Area for AI Responses
        ta_ai_response = lv_textarea_create(tab_ai);
        lv_obj_set_size(ta_ai_response, 228, 112);
        lv_obj_align(ta_ai_response, LV_ALIGN_TOP_MID, 0, 74);
        lv_obj_set_style_bg_color(ta_ai_response, lv_color_hex(0x0E1726), 0);
        lv_obj_set_style_text_color(ta_ai_response, lv_color_hex(0xE2E8F0), 0);
        lv_obj_set_style_border_color(ta_ai_response, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_radius(ta_ai_response, 10, 0);
        lv_obj_set_style_text_font(ta_ai_response, &font_vietnamese_14, 0);
        lv_textarea_set_text(ta_ai_response, "Xin chào! Tôi là Trợ Lý NALA AI.\nNhấn giữ nút bên dưới để nói chuyện với tôi...");

        // Large PTT Button
        btn_ai_ptt = lv_btn_create(tab_ai);
        lv_obj_set_size(btn_ai_ptt, 228, 44);
        lv_obj_align(btn_ai_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_radius(btn_ai_ptt, 22, 0);
        lv_obj_add_event_cb(btn_ai_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_ai_ptt_text = lv_label_create(btn_ai_ptt);
        lv_obj_clear_flag(lbl_ai_ptt_text, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_ai_ptt_text, "GIỮ ĐỂ NÓI VỚI NALA AI");
        lv_obj_set_style_text_font(lbl_ai_ptt_text, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ai_ptt_text);
    }

    void build_tab_intercom() {
        lv_obj_clear_flag(tab_intercom, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_intercom, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_intercom, 4, 0);

        lbl_intercom_status = lv_label_create(tab_intercom);
        lv_label_set_text(lbl_intercom_status, "Đàm thoại: Sẵn sàng");
        lv_obj_set_style_text_color(lbl_intercom_status, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_intercom_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_intercom_status, LV_ALIGN_TOP_MID, 0, 4);

        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = lv_btn_create(tab_intercom);
            lv_obj_set_size(btn_rooms[i], 108, 36);
            int x = (i % 2 == 0) ? 4 : 120;
            int y = 26 + (i / 2) * 40;
            lv_obj_set_pos(btn_rooms[i], x, y);
            lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x111927), 0);
            lv_obj_set_style_border_color(btn_rooms[i], lv_color_hex(0x27354A), 0);
            lv_obj_set_style_border_width(btn_rooms[i], 1, 0);
            lv_obj_set_style_radius(btn_rooms[i], 10, 0);
            lv_obj_add_event_cb(btn_rooms[i], event_handler_trampoline, LV_EVENT_CLICKED, this);

            lbl_rooms[i] = lv_label_create(btn_rooms[i]);
            lv_obj_clear_flag(lbl_rooms[i], LV_OBJ_FLAG_CLICKABLE);
            lv_label_set_text_fmt(lbl_rooms[i], "Phòng %d", i + 1);
            lv_obj_set_style_text_font(lbl_rooms[i], &font_vietnamese_14, 0);
            lv_obj_center(lbl_rooms[i]);
            lv_obj_add_flag(btn_rooms[i], LV_OBJ_FLAG_HIDDEN);
        }

        btn_broadcast = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_broadcast, 224, 36);
        lv_obj_align(btn_broadcast, LV_ALIGN_TOP_MID, 0, 108);
        lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x1E3A8A), 0);
        lv_obj_set_style_border_color(btn_broadcast, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_broadcast, 1, 0);
        lv_obj_set_style_radius(btn_broadcast, 10, 0);
        lv_obj_add_event_cb(btn_broadcast, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lv_obj_t* lbl_all = lv_label_create(btn_broadcast);
        lv_obj_clear_flag(lbl_all, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_all, "GỌI TOÀN NHÀ (ALL)");
        lv_obj_set_style_text_font(lbl_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_all);

        btn_intercom_ptt = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_intercom_ptt, 224, 44);
        lv_obj_align(btn_intercom_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_radius(btn_intercom_ptt, 22, 0);
        lv_obj_add_event_cb(btn_intercom_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_intercom_ptt = lv_label_create(btn_intercom_ptt);
        lv_obj_clear_flag(lbl_intercom_ptt, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_intercom_ptt, "NHẤN GIỮ ĐỂ NÓI");
        lv_obj_set_style_text_font(lbl_intercom_ptt, &font_vietnamese_14, 0);
        lv_obj_center(lbl_intercom_ptt);
    }

    void build_tab_settings(uint8_t init_vol, uint8_t init_bright, uint8_t init_mic_gain = 5) {
        lv_obj_clear_flag(tab_settings, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_settings, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_settings, 4, 0);

        // 1. Âm lượng Loa (Y: 0..16)
        lv_obj_t* lbl_vol = lv_label_create(tab_settings);
        lv_label_set_text(lbl_vol, "Âm Lượng:");
        lv_obj_set_style_text_font(lbl_vol, &font_vietnamese_14, 0);
        lv_obj_align(lbl_vol, LV_ALIGN_TOP_LEFT, 4, 0);

        lbl_vol_val = lv_label_create(tab_settings);
        lv_label_set_text_fmt(lbl_vol_val, "%d%%", init_vol);
        lv_obj_set_style_text_color(lbl_vol_val, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_vol_val, &font_vietnamese_14, 0);
        lv_obj_align(lbl_vol_val, LV_ALIGN_TOP_RIGHT, -4, 0);

        slider_vol = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_vol, 224, 7);
        lv_obj_align(slider_vol, LV_ALIGN_TOP_MID, 0, 15);
        lv_slider_set_range(slider_vol, 0, 100);
        lv_slider_set_value(slider_vol, init_vol, LV_ANIM_OFF);
        lv_obj_set_style_bg_color(slider_vol, lv_color_hex(0x1E293B), LV_PART_MAIN);
        lv_obj_set_style_bg_color(slider_vol, lv_color_hex(0x38BDF8), LV_PART_INDICATOR);
        lv_obj_add_event_cb(slider_vol, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        // 2. Độ sáng Màn hình (Y: 23..39)
        lv_obj_t* lbl_br = lv_label_create(tab_settings);
        lv_label_set_text(lbl_br, "Độ Sáng:");
        lv_obj_set_style_text_font(lbl_br, &font_vietnamese_14, 0);
        lv_obj_align(lbl_br, LV_ALIGN_TOP_LEFT, 4, 23);

        lbl_bright_val = lv_label_create(tab_settings);
        lv_label_set_text_fmt(lbl_bright_val, "%d", init_bright);
        lv_obj_set_style_text_color(lbl_bright_val, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_bright_val, &font_vietnamese_14, 0);
        lv_obj_align(lbl_bright_val, LV_ALIGN_TOP_RIGHT, -4, 23);

        slider_bright = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_bright, 224, 7);
        lv_obj_align(slider_bright, LV_ALIGN_TOP_MID, 0, 38);
        lv_slider_set_range(slider_bright, 20, 255);
        lv_slider_set_value(slider_bright, init_bright, LV_ANIM_OFF);
        lv_obj_set_style_bg_color(slider_bright, lv_color_hex(0x1E293B), LV_PART_MAIN);
        lv_obj_set_style_bg_color(slider_bright, lv_color_hex(0x38BDF8), LV_PART_INDICATOR);
        lv_obj_add_event_cb(slider_bright, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        // 3. Độ Nhạy Mic (Y: 46..62)
        lv_obj_t* lbl_mc = lv_label_create(tab_settings);
        lv_label_set_text(lbl_mc, "Độ Nhạy Mic:");
        lv_obj_set_style_text_font(lbl_mc, &font_vietnamese_14, 0);
        lv_obj_align(lbl_mc, LV_ALIGN_TOP_LEFT, 4, 46);

        lbl_mic_val = lv_label_create(tab_settings);
        const char* gain_names[8] = {"", "Thấp", "Vừa", "Chuẩn", "Nhạy", "Rất nhạy", "Cực nhạy", "Tối đa"};
        char m_buf[32];
        snprintf(m_buf, sizeof(m_buf), "Mức %d (%s)", init_mic_gain, (init_mic_gain >= 1 && init_mic_gain <= 7) ? gain_names[init_mic_gain] : "");
        lv_label_set_text(lbl_mic_val, m_buf);
        lv_obj_set_style_text_color(lbl_mic_val, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_mic_val, &font_vietnamese_14, 0);
        lv_obj_align(lbl_mic_val, LV_ALIGN_TOP_RIGHT, -4, 46);

        slider_mic = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_mic, 224, 7);
        lv_obj_align(slider_mic, LV_ALIGN_TOP_MID, 0, 61);
        lv_slider_set_range(slider_mic, 1, 7);
        lv_slider_set_value(slider_mic, init_mic_gain, LV_ANIM_OFF);
        lv_obj_set_style_bg_color(slider_mic, lv_color_hex(0x1E293B), LV_PART_MAIN);
        lv_obj_set_style_bg_color(slider_mic, lv_color_hex(0x38BDF8), LV_PART_INDICATOR);
        lv_obj_add_event_cb(slider_mic, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        // 4. Grid 4 Nút Chẩn Đoán (Y: 72..138)
        btn_test_speaker = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_speaker, 108, 30);
        lv_obj_set_pos(btn_test_speaker, 4, 72);
        lv_obj_set_style_bg_color(btn_test_speaker, lv_color_hex(0x1E3A8A), 0);
        lv_obj_set_style_radius(btn_test_speaker, 6, 0);
        lv_obj_add_event_cb(btn_test_speaker, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ts = lv_label_create(btn_test_speaker);
        lv_label_set_text(lbl_ts, "TEST LOA");
        lv_obj_set_style_text_font(lbl_ts, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ts);

        btn_test_mic = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_mic, 108, 30);
        lv_obj_set_pos(btn_test_mic, 120, 72);
        lv_obj_set_style_bg_color(btn_test_mic, lv_color_hex(0x065F46), 0);
        lv_obj_set_style_radius(btn_test_mic, 6, 0);
        lv_obj_add_event_cb(btn_test_mic, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tm = lv_label_create(btn_test_mic);
        lv_label_set_text(lbl_tm, "TEST MIC");
        lv_obj_set_style_text_font(lbl_tm, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tm);

        btn_test_ws = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_ws, 108, 30);
        lv_obj_set_pos(btn_test_ws, 4, 106);
        lv_obj_set_style_bg_color(btn_test_ws, lv_color_hex(0x581C87), 0);
        lv_obj_set_style_radius(btn_test_ws, 6, 0);
        lv_obj_add_event_cb(btn_test_ws, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tw = lv_label_create(btn_test_ws);
        lv_label_set_text(lbl_tw, "TEST SERVER");
        lv_obj_set_style_text_font(lbl_tw, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tw);

        btn_enter_ap = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_enter_ap, 108, 30);
        lv_obj_set_pos(btn_enter_ap, 120, 106);
        lv_obj_set_style_bg_color(btn_enter_ap, lv_color_hex(0x92400E), 0);
        lv_obj_set_style_radius(btn_enter_ap, 6, 0);
        lv_obj_add_event_cb(btn_enter_ap, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ap = lv_label_create(btn_enter_ap);
        lv_label_set_text(lbl_ap, "ĐỔI WIFI");
        lv_obj_set_style_text_font(lbl_ap, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ap);

        // 5. Khung Hiển Thị Kết Quả Chẩn Đoán (Y: 142, H: 28)
        lv_obj_t* box_diag = lv_obj_create(tab_settings);
        lv_obj_set_size(box_diag, 224, 28);
        lv_obj_set_pos(box_diag, 4, 142);
        lv_obj_set_style_bg_color(box_diag, lv_color_hex(0x111827), 0);
        lv_obj_set_style_border_color(box_diag, lv_color_hex(0x1F2937), 0);
        lv_obj_set_style_radius(box_diag, 6, 0);
        lv_obj_set_style_pad_all(box_diag, 2, 0);
        lv_obj_clear_flag(box_diag, LV_OBJ_FLAG_SCROLLABLE);

        lbl_diag_result = lv_label_create(box_diag);
        lv_label_set_text(lbl_diag_result, "Chẩn đoán: Sẵn sàng");
        lv_obj_set_style_text_color(lbl_diag_result, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_diag_result, &font_vietnamese_14, 0);
        lv_obj_center(lbl_diag_result);

        // 6. Kiểm tra OTA & Toggle Chuông (Y: 174, H: 24)
        btn_check_ota = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_check_ota, 108, 24);
        lv_obj_set_pos(btn_check_ota, 4, 174);
        lv_obj_set_style_bg_color(btn_check_ota, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_radius(btn_check_ota, 6, 0);
        lv_obj_set_style_pad_all(btn_check_ota, 0, 0);
        lv_obj_add_event_cb(btn_check_ota, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ota = lv_label_create(btn_check_ota);
        lv_obj_clear_flag(lbl_ota, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_ota, "KIỂM TRA OTA");
        lv_obj_set_style_text_font(lbl_ota, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ota);

        btn_toggle_ring = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_toggle_ring, 108, 24);
        lv_obj_set_pos(btn_toggle_ring, 120, 174);
        lv_obj_set_style_bg_color(btn_toggle_ring, ring_on_call_enabled ? lv_color_hex(0x0284C7) : lv_color_hex(0x334155), 0);
        lv_obj_set_style_radius(btn_toggle_ring, 6, 0);
        lv_obj_set_style_pad_all(btn_toggle_ring, 0, 0);
        lv_obj_add_event_cb(btn_toggle_ring, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_toggle_ring = lv_label_create(btn_toggle_ring);
        lv_obj_clear_flag(lbl_toggle_ring, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_toggle_ring, ring_on_call_enabled ? "CHUÔNG: BẬT" : "CHUÔNG: TẮT");
        lv_obj_set_style_text_font(lbl_toggle_ring, &font_vietnamese_14, 0);
        lv_obj_center(lbl_toggle_ring);

        // 7. Thông tin Firmware & Hướng dẫn (Y: 202..230)
        lbl_firmware_ver = lv_label_create(tab_settings);
        lv_label_set_text(lbl_firmware_ver, "Bản: v2.9.2 | PSRAM: 0.0MB");
        lv_obj_set_style_text_color(lbl_firmware_ver, lv_color_hex(0x34D399), 0);
        lv_obj_set_style_text_font(lbl_firmware_ver, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_firmware_ver, 4, 202);

        lbl_net_info = lv_label_create(tab_settings);
        lv_label_set_text(lbl_net_info, "Chạm giữ Header 2s để đổi WiFi.");
        lv_obj_set_style_text_color(lbl_net_info, lv_color_hex(0x64748B), 0);
        lv_obj_set_style_text_font(lbl_net_info, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_net_info, 4, 218);
    }

    void build_incoming_call_modal(lv_obj_t* parent) {
        modal_incoming_call = lv_obj_create(parent);
        lv_obj_set_size(modal_incoming_call, 230, 130);
        lv_obj_align(modal_incoming_call, LV_ALIGN_CENTER, 0, -10);
        lv_obj_set_style_bg_color(modal_incoming_call, lv_color_hex(0x0B1326), 0);
        lv_obj_set_style_border_color(modal_incoming_call, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(modal_incoming_call, 2, 0);
        lv_obj_set_style_radius(modal_incoming_call, 14, 0);
        lv_obj_set_style_shadow_width(modal_incoming_call, 24, 0);
        lv_obj_set_style_shadow_color(modal_incoming_call, lv_color_hex(0x000000), 0);
        lv_obj_clear_flag(modal_incoming_call, LV_OBJ_FLAG_SCROLLABLE);

        lbl_incoming_title = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_title, "CUỘC GỌI NỘI BỘ");
        lv_obj_set_style_text_color(lbl_incoming_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_incoming_title, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_title, LV_ALIGN_TOP_MID, 0, 4);

        lbl_incoming_caller = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_caller, "Đang kết nối...");
        lv_obj_set_style_text_color(lbl_incoming_caller, lv_color_hex(0xFFFFFF), 0);
        lv_obj_set_style_text_font(lbl_incoming_caller, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_caller, LV_ALIGN_CENTER, 0, -4);

        lbl_incoming_status = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_status, "Đang đàm thoại trực tiếp...");
        lv_obj_set_style_text_color(lbl_incoming_status, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_incoming_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_status, LV_ALIGN_BOTTOM_MID, 0, -6);

        lv_obj_add_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);
    }

    void build_climate_dialog(lv_obj_t* parent) {
        dialog_climate = lv_obj_create(parent);
        lv_obj_set_size(dialog_climate, 234, 260);
        lv_obj_center(dialog_climate);
        lv_obj_set_style_bg_color(dialog_climate, lv_color_hex(0x0B1326), 0);
        lv_obj_set_style_bg_opa(dialog_climate, LV_OPA_COVER, 0);
        lv_obj_set_style_border_color(dialog_climate, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(dialog_climate, 2, 0);
        lv_obj_set_style_radius(dialog_climate, 12, 0);
        lv_obj_set_style_pad_all(dialog_climate, 4, 0);
        lv_obj_clear_flag(dialog_climate, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_flag(dialog_climate, LV_OBJ_FLAG_HIDDEN);

        // 1. Header: Tiêu đề + Nút Đóng [X]
        lbl_clim_title = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_title, "ĐIỀU KHIỂN MÁY LẠNH");
        lv_obj_set_style_text_color(lbl_clim_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_clim_title, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_clim_title, 6, 4);

        btn_clim_close = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_close, 26, 26);
        lv_obj_set_pos(btn_clim_close, 194, 2);
        lv_obj_set_style_radius(btn_clim_close, 13, 0);
        lv_obj_set_style_bg_color(btn_clim_close, lv_color_hex(0x334155), 0);
        lv_obj_set_style_border_color(btn_clim_close, lv_color_hex(0x64748B), 0);
        lv_obj_set_style_border_width(btn_clim_close, 1, 0);
        lv_obj_set_style_pad_all(btn_clim_close, 0, 0);
        lv_obj_add_event_cb(btn_clim_close, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_cx = lv_label_create(btn_clim_close);
        lv_obj_clear_flag(lbl_cx, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_cx, "X");
        lv_obj_set_style_text_color(lbl_cx, lv_color_hex(0xFFFFFF), 0);
        lv_obj_set_style_text_font(lbl_cx, &font_vietnamese_14, 0);
        lv_obj_center(lbl_cx);

        // 2. Stepper [-0.5] [26.0°C] [+0.5]
        btn_clim_minus = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_minus, 50, 44);
        lv_obj_set_pos(btn_clim_minus, 4, 32);
        lv_obj_set_style_bg_color(btn_clim_minus, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_minus, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_clim_minus, 1, 0);
        lv_obj_set_style_radius(btn_clim_minus, 10, 0);
        lv_obj_add_event_cb(btn_clim_minus, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_cm = lv_label_create(btn_clim_minus);
        lv_obj_clear_flag(lbl_cm, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_cm, "-0.5");
        lv_obj_set_style_text_font(lbl_cm, &font_vietnamese_14, 0);
        lv_obj_center(lbl_cm);

        lbl_clim_temp = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_temp, "26.0°C");
        lv_obj_set_style_text_color(lbl_clim_temp, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_clim_temp, &font_vietnamese_16, 0);
        lv_obj_set_pos(lbl_clim_temp, 84, 38);

        btn_clim_plus = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_plus, 50, 44);
        lv_obj_set_pos(btn_clim_plus, 172, 32);
        lv_obj_set_style_bg_color(btn_clim_plus, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_plus, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_clim_plus, 1, 0);
        lv_obj_set_style_radius(btn_clim_plus, 10, 0);
        lv_obj_add_event_cb(btn_clim_plus, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_cp = lv_label_create(btn_clim_plus);
        lv_obj_clear_flag(lbl_cp, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_cp, "+0.5");
        lv_obj_set_style_text_font(lbl_cp, &font_vietnamese_14, 0);
        lv_obj_center(lbl_cp);

        // Status Line
        lbl_clim_status = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_status, "Phòng: 28.0°C - Đang Làm Mát");
        lv_obj_set_style_text_color(lbl_clim_status, lv_color_hex(0x06B6D4), 0);
        lv_obj_set_style_text_font(lbl_clim_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_clim_status, LV_ALIGN_TOP_MID, 0, 80);

        // 3. Grid 4 Chế Độ HVAC
        const char* mode_names[] = {"LÀM MÁT", "QUẠT", "HÚT ẨM", "TỰ ĐỘNG"};
        for (int i = 0; i < 4; i++) {
            btn_clim_modes[i] = lv_btn_create(dialog_climate);
            lv_obj_set_size(btn_clim_modes[i], 52, 28);
            int mx = 4 + i * 56;
            lv_obj_set_pos(btn_clim_modes[i], mx, 100);
            lv_obj_set_style_bg_color(btn_clim_modes[i], lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(btn_clim_modes[i], lv_color_hex(0x334155), 0);
            lv_obj_set_style_border_width(btn_clim_modes[i], 1, 0);
            lv_obj_set_style_radius(btn_clim_modes[i], 6, 0);
            lv_obj_set_style_pad_all(btn_clim_modes[i], 0, 0);
            lv_obj_add_event_cb(btn_clim_modes[i], event_handler_trampoline, LV_EVENT_CLICKED, this);

            lbl_clim_modes[i] = lv_label_create(btn_clim_modes[i]);
            lv_obj_clear_flag(lbl_clim_modes[i], LV_OBJ_FLAG_CLICKABLE);
            lv_label_set_text(lbl_clim_modes[i], mode_names[i]);
            lv_obj_set_style_text_font(lbl_clim_modes[i], &font_vietnamese_14, 0);
            lv_obj_center(lbl_clim_modes[i]);
        }

        // 4. Hàng Nút Phụ
        btn_clim_power = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_power, 108, 32);
        lv_obj_set_pos(btn_clim_power, 4, 134);
        lv_obj_set_style_bg_color(btn_clim_power, lv_color_hex(0x059669), 0);
        lv_obj_set_style_radius(btn_clim_power, 8, 0);
        lv_obj_add_event_cb(btn_clim_power, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_clim_power = lv_label_create(btn_clim_power);
        lv_obj_clear_flag(lbl_clim_power, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_clim_power, "BẬT NGUỒN");
        lv_obj_set_style_text_font(lbl_clim_power, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_power);

        btn_clim_fan = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_fan, 108, 32);
        lv_obj_set_pos(btn_clim_fan, 116, 134);
        lv_obj_set_style_bg_color(btn_clim_fan, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_fan, lv_color_hex(0x334155), 0);
        lv_obj_set_style_border_width(btn_clim_fan, 1, 0);
        lv_obj_set_style_radius(btn_clim_fan, 8, 0);
        lv_obj_add_event_cb(btn_clim_fan, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_clim_fan = lv_label_create(btn_clim_fan);
        lv_obj_clear_flag(lbl_clim_fan, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_clim_fan, "Quạt: Tự Động");
        lv_obj_set_style_text_font(lbl_clim_fan, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_fan);

        btn_clim_eco26 = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_eco26, 108, 32);
        lv_obj_set_pos(btn_clim_eco26, 4, 172);
        lv_obj_set_style_bg_color(btn_clim_eco26, lv_color_hex(0x065F46), 0);
        lv_obj_set_style_radius(btn_clim_eco26, 8, 0);
        lv_obj_add_event_cb(btn_clim_eco26, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_e26 = lv_label_create(btn_clim_eco26);
        lv_obj_clear_flag(lbl_e26, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_e26, "ECO 26°C");
        lv_obj_set_style_text_font(lbl_e26, &font_vietnamese_14, 0);
        lv_obj_center(lbl_e26);

        btn_clim_swing = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_swing, 108, 32);
        lv_obj_set_pos(btn_clim_swing, 116, 172);
        lv_obj_set_style_bg_color(btn_clim_swing, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_swing, lv_color_hex(0x334155), 0);
        lv_obj_set_style_border_width(btn_clim_swing, 1, 0);
        lv_obj_set_style_radius(btn_clim_swing, 8, 0);
        lv_obj_add_event_cb(btn_clim_swing, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_clim_swing = lv_label_create(btn_clim_swing);
        lv_obj_clear_flag(lbl_clim_swing, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_clim_swing, "Đảo Gió: TẮT");
        lv_obj_set_style_text_font(lbl_clim_swing, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_swing);

        // 5. Strip Info
        lbl_clim_info = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_info, "Phòng: 28.0°C | Cài đặt: 26.0°C");
        lv_obj_set_style_text_color(lbl_clim_info, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_clim_info, &font_vietnamese_14, 0);
        lv_obj_align(lbl_clim_info, LV_ALIGN_BOTTOM_MID, 0, -4);
    }

    void open_climate_dialog(int btn_idx) {
        if (btn_idx < 0 || btn_idx >= MAX_DASHBOARD_BUTTONS) return;
        active_climate_idx = btn_idx;
        update_climate_dialog_ui();
        if (dialog_climate) {
            lv_obj_clear_flag(dialog_climate, LV_OBJ_FLAG_HIDDEN);
            lv_obj_move_foreground(dialog_climate);
        }
    }

    void close_climate_dialog() {
        if (dialog_climate) {
            lv_obj_add_flag(dialog_climate, LV_OBJ_FLAG_HIDDEN);
        }
        active_climate_idx = -1;
    }

    void update_climate_dialog_ui() {
        if (active_climate_idx < 0 || active_climate_idx >= MAX_DASHBOARD_BUTTONS) return;
        UIButtonSlot& b = buttons[active_climate_idx];

        if (lbl_clim_title) {
            char title_buf[64];
            snprintf(title_buf, sizeof(title_buf), "%s", b.name.c_str());
            lv_label_set_text(lbl_clim_title, title_buf);
        }

        if (lbl_clim_temp) {
            char temp_buf[32];
            snprintf(temp_buf, sizeof(temp_buf), "%.1f°C", b.temperature > 10.0f ? b.temperature : 26.0f);
            lv_label_set_text(lbl_clim_temp, temp_buf);
        }

        if (lbl_clim_status) {
            float room_t = b.current_temperature > 10.0f ? b.current_temperature : 28.0f;
            const char* st_name = "Tắt";
            uint32_t st_color = 0x94A3B8;
            if (b.is_on && b.hvac_mode != "off") {
                if (b.hvac_mode == "cool") {
                    st_name = "Đang Làm Mát";
                    st_color = 0x06B6D4;
                } else if (b.hvac_mode == "fan_only") {
                    st_name = "Quạt Gió";
                    st_color = 0xA78BFA;
                } else if (b.hvac_mode == "dry") {
                    st_name = "Hút Ẩm";
                    st_color = 0x10B981;
                } else if (b.hvac_mode == "auto") {
                    st_name = "Tự Động";
                    st_color = 0xF59E0B;
                }
            }
            char st_buf[64];
            snprintf(st_buf, sizeof(st_buf), "Phòng: %.1f°C - %s", room_t, st_name);
            lv_label_set_text(lbl_clim_status, st_buf);
            lv_obj_set_style_text_color(lbl_clim_status, lv_color_hex(st_color), 0);
        }

        const char* mode_keys[] = {"cool", "fan_only", "dry", "auto"};
        for (int i = 0; i < 4; i++) {
            if (!btn_clim_modes[i]) continue;
            bool is_active = (b.is_on && b.hvac_mode == mode_keys[i]);
            if (is_active) {
                lv_obj_set_style_bg_color(btn_clim_modes[i], lv_color_hex(0x0284C7), 0);
                lv_obj_set_style_border_color(btn_clim_modes[i], lv_color_hex(0x38BDF8), 0);
                lv_obj_set_style_border_width(btn_clim_modes[i], 2, 0);
            } else {
                lv_obj_set_style_bg_color(btn_clim_modes[i], lv_color_hex(0x1E293B), 0);
                lv_obj_set_style_border_color(btn_clim_modes[i], lv_color_hex(0x334155), 0);
                lv_obj_set_style_border_width(btn_clim_modes[i], 1, 0);
            }
        }

        if (btn_clim_power && lbl_clim_power) {
            if (b.is_on && b.hvac_mode != "off") {
                lv_obj_set_style_bg_color(btn_clim_power, lv_color_hex(0xDC2626), 0);
                lv_label_set_text(lbl_clim_power, "TẮT NGUỒN");
            } else {
                lv_obj_set_style_bg_color(btn_clim_power, lv_color_hex(0x059669), 0);
                lv_label_set_text(lbl_clim_power, "BẬT NGUỒN");
            }
        }

        if (lbl_clim_fan) {
            const char* fan_lbl = "Quạt: Tự Động";
            if (b.fan_mode == "low") fan_lbl = "Quạt: Nhẹ";
            else if (b.fan_mode == "medium") fan_lbl = "Quạt: Vừa";
            else if (b.fan_mode == "high") fan_lbl = "Quạt: Mạnh";
            lv_label_set_text(lbl_clim_fan, fan_lbl);
        }

        if (btn_clim_swing && lbl_clim_swing) {
            if (b.swing_on) {
                lv_obj_set_style_bg_color(btn_clim_swing, lv_color_hex(0x0284C7), 0);
                lv_label_set_text(lbl_clim_swing, "Đảo Gió: BẬT");
            } else {
                lv_obj_set_style_bg_color(btn_clim_swing, lv_color_hex(0x1E293B), 0);
                lv_label_set_text(lbl_clim_swing, "Đảo Gió: TẮT");
            }
        }

        if (lbl_clim_info) {
            float room_t = b.current_temperature > 10.0f ? b.current_temperature : 28.0f;
            float set_t = b.temperature > 10.0f ? b.temperature : 26.0f;
            char if_buf[64];
            snprintf(if_buf, sizeof(if_buf), "Phòng: %.1f°C | Cài đặt: %.1f°C", room_t, set_t);
            lv_label_set_text(lbl_clim_info, if_buf);
        }
    }
};

extern UILVGLDashboard uiDashboard;
