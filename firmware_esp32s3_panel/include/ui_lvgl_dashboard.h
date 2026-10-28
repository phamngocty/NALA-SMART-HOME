#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - LVGL 8.3.11 DASHBOARD (FULL ACCENTED VIETNAMESE)
 * - 100% Vietnamese Font (Tahoma 14 & 16) with all diacritics
 * - Pre-allocated 4 buttons in 2x2 grid (NO dynamic alloc/delete -> 100% Crash-free)
 * - Direct Touch Button & Header Hold to enter Soft-AP (192.168.4.1)
 * ==============================================================================
 */

#include <Arduino.h>
#include <lvgl.h>
#include <ArduinoJson.h>
#include "font_vietnamese.h"

typedef void (*UIActionCallback_t)(const char* target, const char* action, int value);

struct UIButtonSlot {
    lv_obj_t* btn_obj;
    lv_obj_t* lbl_obj;
    String id;
    String name;
    String entity_id;
    String icon;
    bool is_on;
};

class UILVGLDashboard {
private:
    lv_obj_t* tabview;
    lv_obj_t* tab_home;
    lv_obj_t* tab_intercom;
    lv_obj_t* tab_settings;

    // Header Info
    lv_obj_t* header_obj;
    lv_obj_t* lbl_header_title;
    lv_obj_t* lbl_header_info;

    // Tab 1 Elements (Fixed pre-allocated 4 buttons)
    UIButtonSlot buttons[4];
    uint8_t active_buttons_count;
    lv_obj_t* lbl_ai_state;
    lv_obj_t* ta_ai_response;
    lv_obj_t* btn_ai_ptt;
    lv_obj_t* lbl_ai_ptt_text;

    // Tab 2 Elements
    struct IntercomTarget {
        uint8_t id = 0;
        char name[28] = {0};
        bool is_online = false;
    };
    IntercomTarget intercom_targets[4];
    uint8_t active_intercom_targets_count;

    lv_obj_t* btn_rooms[4];
    lv_obj_t* lbl_rooms[4];
    lv_obj_t* btn_broadcast;
    lv_obj_t* btn_intercom_ptt;
    lv_obj_t* lbl_intercom_ptt;
    lv_obj_t* lbl_intercom_status;
    int selected_room_idx;

    // Tab 3 Elements
    lv_obj_t* slider_vol;
    lv_obj_t* lbl_vol_val;
    lv_obj_t* slider_bright;
    lv_obj_t* lbl_bright_val;
    lv_obj_t* dd_ai_model;
    lv_obj_t* btn_enter_ap;
    lv_obj_t* btn_test_speaker;
    lv_obj_t* btn_test_mic;
    lv_obj_t* btn_test_ws;
    lv_obj_t* lbl_diag_result;
    lv_obj_t* lbl_net_info;

    UIActionCallback_t action_cb;

public:
    UILVGLDashboard() 
        : tabview(nullptr), tab_home(nullptr), tab_intercom(nullptr), tab_settings(nullptr),
          header_obj(nullptr), lbl_header_title(nullptr), lbl_header_info(nullptr),
          active_buttons_count(2), lbl_ai_state(nullptr), ta_ai_response(nullptr),
          btn_ai_ptt(nullptr), lbl_ai_ptt_text(nullptr),
          active_intercom_targets_count(0),
          btn_broadcast(nullptr), btn_intercom_ptt(nullptr), lbl_intercom_ptt(nullptr),
          lbl_intercom_status(nullptr),
          selected_room_idx(0xFF),
          slider_vol(nullptr), lbl_vol_val(nullptr), slider_bright(nullptr), lbl_bright_val(nullptr),
          dd_ai_model(nullptr), btn_enter_ap(nullptr),
          btn_test_speaker(nullptr), btn_test_mic(nullptr), btn_test_ws(nullptr),
          lbl_diag_result(nullptr), lbl_net_info(nullptr),
          action_cb(nullptr) {
        
        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = nullptr;
            lbl_rooms[i] = nullptr;
        }
        
        for (int i = 0; i < 4; i++) {
            buttons[i].btn_obj = nullptr;
            buttons[i].lbl_obj = nullptr;
            buttons[i].is_on = false;
        }
        buttons[0].name = "Đèn Phòng";
        buttons[0].entity_id = "light.moes_matter_switch_den_3_6";
        buttons[0].icon = "light";

        buttons[1].name = "Máy Lạnh";
        buttons[1].entity_id = "climate.151732606266034_climate";
        buttons[1].icon = "climate";

        buttons[2].name = "Quạt Trần";
        buttons[2].entity_id = "fan.phong_khach";
        buttons[2].icon = "fan";

        buttons[3].name = "Rèm Cửa";
        buttons[3].entity_id = "cover.phong_khach";
        buttons[3].icon = "cover";
    }

    void set_action_callback(UIActionCallback_t cb) {
        action_cb = cb;
    }

    void init(const char* room_name, const char* ip_str, const char* pair_code, uint8_t init_vol, uint8_t init_bright) {
        lv_obj_t* scr = lv_scr_act();
        lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(scr, lv_color_hex(0x0B0F19), 0);

        // Header trên cùng (Cao 38px)
        header_obj = lv_obj_create(scr);
        lv_obj_set_size(header_obj, 240, 38);
        lv_obj_align(header_obj, LV_ALIGN_TOP_MID, 0, 0);
        lv_obj_set_style_bg_color(header_obj, lv_color_hex(0x111827), 0);
        lv_obj_set_style_border_side(header_obj, LV_BORDER_SIDE_BOTTOM, 0);
        lv_obj_set_style_border_color(header_obj, lv_color_hex(0x1F2937), 0);
        lv_obj_set_style_border_width(header_obj, 1, 0);
        lv_obj_set_style_pad_all(header_obj, 3, 0);
        lv_obj_clear_flag(header_obj, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(header_obj, event_handler_trampoline, LV_EVENT_LONG_PRESSED, this);

        lbl_header_title = lv_label_create(header_obj);
        lv_label_set_text_fmt(lbl_header_title, "NALA: %s", room_name && strlen(room_name) > 0 ? room_name : "Phòng Khách");
        lv_obj_set_style_text_color(lbl_header_title, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_header_title, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_title, LV_ALIGN_TOP_LEFT, 4, -1);

        lbl_header_info = lv_label_create(header_obj);
        lv_label_set_text_fmt(lbl_header_info, "IP: %s | Mã: [%s]", ip_str ? ip_str : "192.168.1.x", pair_code ? pair_code : "881C");
        lv_obj_set_style_text_color(lbl_header_info, lv_color_hex(0x9CA3AF), 0);
        lv_obj_set_style_text_font(lbl_header_info, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_info, LV_ALIGN_BOTTOM_LEFT, 4, 1);

        // TabView (Dưới Header, Cao 282px)
        tabview = lv_tabview_create(scr, LV_DIR_BOTTOM, 36);
        lv_obj_set_size(tabview, 240, 282);
        lv_obj_align(tabview, LV_ALIGN_BOTTOM_MID, 0, 0);
        lv_obj_set_style_bg_color(tabview, lv_color_hex(0x0B0F19), 0);

        // Tab Buttons Bar Styling với Font Tiếng Việt
        lv_obj_t* tab_btns = lv_tabview_get_tab_btns(tabview);
        lv_obj_set_style_bg_color(tab_btns, lv_color_hex(0x111827), 0);
        lv_obj_set_style_text_color(tab_btns, lv_color_hex(0x9CA3AF), 0);
        lv_obj_set_style_text_font(tab_btns, &font_vietnamese_14, 0);

        tab_home = lv_tabview_add_tab(tabview, "Nhà & AI");
        tab_intercom = lv_tabview_add_tab(tabview, "Đàm Thoại");
        tab_settings = lv_tabview_add_tab(tabview, "Cài Đặt");

        build_tab_home();
        build_tab_intercom();
        build_tab_settings(init_vol, init_bright);
    }

    // Đồng bộ danh sách nút bấm tùy chỉnh từ Server (Hoàn toàn thread-safe, không xóa object)
    void sync_buttons(const JsonArrayConst& btn_array) {
        uint8_t count = btn_array.size();
        if (count > 4) count = 4;
        if (count == 0) count = 1;
        active_buttons_count = count;

        for (uint8_t i = 0; i < count; i++) {
            buttons[i].id = btn_array[i]["id"] | String("btn_" + String(i+1));
            buttons[i].name = btn_array[i]["name"] | String("Nút " + String(i+1));
            buttons[i].entity_id = btn_array[i]["entity_id"] | "";
            buttons[i].icon = btn_array[i]["icon"] | "light";

            // Parse trạng thái đồng bộ từ Server/Home Assistant
            bool is_on = btn_array[i]["is_on"] | false;
            if (!is_on && btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                is_on = (st == "on" || (st != "off" && st != "unavailable" && st != "unknown"));
            }
            buttons[i].is_on = is_on;
        }

        // Cập nhật hiển thị và ẩn hiện các nút mà KHÔNG gọi lv_obj_del!
        for (int i = 0; i < 4; i++) {
            if (!buttons[i].btn_obj) continue;
            if (i < active_buttons_count) {
                lv_obj_clear_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                update_button_ui(i);
            } else {
                lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    // Cập nhật trạng thái thiết bị từ Home Assistant (BẬT / TẮT)
    void update_entity_state(const char* entity_id, bool is_on) {
        for (int i = 0; i < 4; i++) {
            if (buttons[i].entity_id.equalsIgnoreCase(entity_id)) {
                buttons[i].is_on = is_on;
                update_button_ui(i);
            }
        }
    }

    // Cập nhật kết quả chẩn đoán trên Tab Cài Đặt (Thread-safe)
    void set_diag_result(const char* text, uint32_t color_hex = 0x10B981) {
        if (lbl_diag_result && text) {
            lv_label_set_text(lbl_diag_result, text);
            lv_obj_set_style_text_color(lbl_diag_result, lv_color_hex(color_hex), 0);
        }
    }

    void set_room_title(const char* name) {
        if (lbl_header_title && name && strlen(name) > 0) {
            lv_label_set_text_fmt(lbl_header_title, "NALA: %s", name);
        }
    }

    void set_ai_state(const char* state_str, const char* response_text = nullptr) {
        if (lbl_ai_state && state_str) {
            if (strcasecmp(state_str, "listening") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang lắng nghe...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x3B82F6), 0);
            } else if (strcasecmp(state_str, "processing") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang suy nghĩ...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0xF59E0B), 0);
            } else if (strcasecmp(state_str, "speaking") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang trả lời...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
            } else {
                lv_label_set_text(lbl_ai_state, "AI: Sẵn sàng (Chờ lệnh)");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
            }
        }
        if (response_text && ta_ai_response && strlen(response_text) > 0) {
            lv_textarea_set_text(ta_ai_response, response_text);
        }
    }

    // Đồng bộ danh sách kênh đàm thoại từ NAS Hub
    void sync_intercom_targets(const JsonArrayConst& targets) {
        active_intercom_targets_count = 0;
        for (JsonObjectConst t : targets) {
            if (active_intercom_targets_count >= 4) break;
            uint8_t tid = t["id"] | (active_intercom_targets_count + 1);
            const char* r_name = t["name"] | "Phòng";
            bool online = t["online"] | false;

            intercom_targets[active_intercom_targets_count].id = tid;
            strncpy(intercom_targets[active_intercom_targets_count].name, r_name, sizeof(intercom_targets[0].name) - 1);
            intercom_targets[active_intercom_targets_count].is_online = online;
            active_intercom_targets_count++;
        }

        // Cập nhật lên UI Tab 2
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

private:
    static void event_handler_trampoline(lv_event_t* e) {
        UILVGLDashboard* self = (UILVGLDashboard*)lv_event_get_user_data(e);
        if (self) self->handle_event(e);
    }

    void handle_event(lv_event_t* e) {
        lv_obj_t* target = lv_event_get_target(e);
        lv_event_code_t code = lv_event_get_code(e);

        // Chạm giữ Header 2s -> Vào chế độ Soft-AP
        if (target == header_obj && code == LV_EVENT_LONG_PRESSED) {
            if (action_cb) action_cb("system", "enter_ap_mode", 0);
            return;
        }

        // Các nút bấm điều khiển Home Assistant
        for (int i = 0; i < 4; i++) {
            if (target == buttons[i].btn_obj && code == LV_EVENT_CLICKED) {
                if (buttons[i].entity_id.length() > 0 && action_cb) {
                    buttons[i].is_on = !buttons[i].is_on;
                    update_button_ui(i);
                    action_cb("entity_toggle", buttons[i].entity_id.c_str(), buttons[i].is_on);
                }
                return;
            }
        }

        // Nút nói chuyện với AI (PTT)
        if (target == btn_ai_ptt) {
            if (code == LV_EVENT_PRESSED) {
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0xEF4444), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "ĐANG THU ÂM (NHẢ ĐỂ GỬI)");
                if (action_cb) action_cb("ptt_ai", "start", 1);
            } else if (code == LV_EVENT_RELEASED) {
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x2563EB), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "GIỮ ĐỂ NÓI VỚI AI");
                if (action_cb) action_cb("ptt_ai", "stop", 0);
            }
            return;
        }

        // Nút đàm thoại nội bộ (Intercom PTT)
        if (target == btn_intercom_ptt) {
            if (code == LV_EVENT_PRESSED) {
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0xEF4444), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "ĐANG ĐÀM THOẠI...");
                set_intercom_status("Đang phát âm thanh...", 0xEF4444);
                if (action_cb) action_cb("ptt_intercom", "start", selected_room_idx);
            } else if (code == LV_EVENT_RELEASED) {
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x059669), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "NHẤN GIỮ ĐỂ NÓI");
                set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                if (action_cb) action_cb("ptt_intercom", "stop", selected_room_idx);
            }
            return;
        }

        // Cài đặt phần cứng
        if (target == slider_vol && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_vol);
            if (lbl_vol_val) lv_label_set_text_fmt(lbl_vol_val, "%d%%", val);
            if (action_cb) action_cb("volume", "set", val);
        } else if (target == slider_bright && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_bright);
            if (lbl_bright_val) lv_label_set_text_fmt(lbl_bright_val, "%d", val);
            if (action_cb) action_cb("brightness", "set", val);
        } else if (target == dd_ai_model && code == LV_EVENT_VALUE_CHANGED) {
            char buf[32];
            lv_dropdown_get_selected_str(dd_ai_model, buf, sizeof(buf));
            if (action_cb) action_cb("ai_model", buf, 0);
        } else if (target == btn_test_speaker && code == LV_EVENT_CLICKED) {
            set_diag_result("Loa: Đang phát âm test...", 0xF59E0B);
            if (action_cb) action_cb("diag_speaker", "start", 0);
        } else if (target == btn_test_mic && code == LV_EVENT_CLICKED) {
            set_diag_result("Mic: Đang thu âm 1.5s...", 0x3B82F6);
            if (action_cb) action_cb("diag_mic", "start", 0);
        } else if (target == btn_test_ws && code == LV_EVENT_CLICKED) {
            set_diag_result("Server: Đang ping NAS Hub...", 0xF59E0B);
            if (action_cb) action_cb("diag_ws", "ping", 0);
        } else if (target == btn_enter_ap && code == LV_EVENT_CLICKED) {
            if (action_cb) action_cb("system", "enter_ap_mode", 0);
        } else {
            for (int i = 0; i < 4; i++) {
                if (target == btn_rooms[i] && code == LV_EVENT_CLICKED) {
                    if (i < active_intercom_targets_count) {
                        selected_room_idx = intercom_targets[i].id;
                    } else {
                        selected_room_idx = i + 1;
                    }
                    highlight_selected_room(i);
                    if (action_cb) action_cb("intercom_target", "select", selected_room_idx);
                    break;
                }
            }
            if (target == btn_broadcast && code == LV_EVENT_CLICKED) {
                selected_room_idx = 0xFF;
                highlight_selected_room(-1);
                if (action_cb) action_cb("intercom_target", "broadcast", 0xFF);
            }
        }
    }

    void update_button_ui(int idx) {
        if (idx < 0 || idx >= 4) return;
        UIButtonSlot& b = buttons[idx];
        if (!b.btn_obj || !b.lbl_obj) return;

        const char* st_text = b.is_on ? "BẬT" : "TẮT";
        lv_label_set_text_fmt(b.lbl_obj, "%s: %s", b.name.c_str(), st_text);

        if (b.is_on) {
            if (b.icon == "climate") {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x059669), 0); // Xanh ngọc
            } else if (b.icon == "fan") {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x06B6D4), 0); // Cyan
            } else if (b.icon == "cover") {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x8B5CF6), 0); // Tím
            } else {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0xF59E0B), 0); // Cam vàng
            }
        } else {
            lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x1F2937), 0); // Xám đậm
        }
    }

    void highlight_selected_room(int idx) {
        for (int i = 0; i < 4; i++) {
            if (btn_rooms[i]) {
                if (i == idx) {
                    lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x2563EB), 0);
                } else {
                    lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x1F2937), 0);
                }
            }
        }
        if (btn_broadcast) {
            if (idx == -1) {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0xD97706), 0);
            } else {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x1F2937), 0);
            }
        }
    }

    void build_tab_home() {
        lv_obj_clear_flag(tab_home, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_home, lv_color_hex(0x0B0F19), 0);
        lv_obj_set_style_pad_all(tab_home, 4, 0);

        // Khởi tạo cố định 4 nút bấm (Grid 2x2: nút 0, 1 hàng 1; nút 2, 3 hàng 2)
        for (int i = 0; i < 4; i++) {
            buttons[i].btn_obj = lv_btn_create(tab_home);
            lv_obj_set_size(buttons[i].btn_obj, 108, 34);
            int x = (i % 2 == 0) ? 4 : 120;
            int y = 4 + (i / 2) * 38;
            lv_obj_set_pos(buttons[i].btn_obj, x, y);
            lv_obj_set_style_radius(buttons[i].btn_obj, 7, 0);
            lv_obj_add_event_cb(buttons[i].btn_obj, event_handler_trampoline, LV_EVENT_CLICKED, this);

            buttons[i].lbl_obj = lv_label_create(buttons[i].btn_obj);
            lv_obj_set_style_text_font(buttons[i].lbl_obj, &font_vietnamese_14, 0);
            lv_obj_center(buttons[i].lbl_obj);

            if (i >= active_buttons_count) {
                lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            } else {
                update_button_ui(i);
            }
        }

        // Nhãn trạng thái AI (Tiếng Việt)
        lbl_ai_state = lv_label_create(tab_home);
        lv_label_set_text(lbl_ai_state, "AI: Sẵn sàng (Chờ lệnh)");
        lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_ai_state, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_ai_state, 6, 82);

        // Khung trả lời văn bản của AI
        ta_ai_response = lv_textarea_create(tab_home);
        lv_obj_set_size(ta_ai_response, 224, 76);
        lv_obj_set_pos(ta_ai_response, 4, 102);
        lv_obj_set_style_bg_color(ta_ai_response, lv_color_hex(0x111827), 0);
        lv_obj_set_style_text_color(ta_ai_response, lv_color_hex(0xE5E7EB), 0);
        lv_obj_set_style_border_color(ta_ai_response, lv_color_hex(0x374151), 0);
        lv_obj_set_style_radius(ta_ai_response, 8, 0);
        lv_obj_set_style_text_font(ta_ai_response, &font_vietnamese_14, 0);
        lv_textarea_set_text(ta_ai_response, "Xin chào! Nhấn giữ nút bên dưới để nói chuyện với Nala AI...");

        // Nút nhấn nói chuyện với AI (PTT)
        btn_ai_ptt = lv_btn_create(tab_home);
        lv_obj_set_size(btn_ai_ptt, 224, 42);
        lv_obj_align(btn_ai_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x2563EB), 0);
        lv_obj_set_style_radius(btn_ai_ptt, 10, 0);
        lv_obj_add_event_cb(btn_ai_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_ai_ptt_text = lv_label_create(btn_ai_ptt);
        lv_label_set_text(lbl_ai_ptt_text, "GIỮ ĐỂ NÓI VỚI AI");
        lv_obj_set_style_text_font(lbl_ai_ptt_text, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ai_ptt_text);
    }

    void build_tab_intercom() {
        lv_obj_clear_flag(tab_intercom, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_intercom, lv_color_hex(0x0B0F19), 0);
        lv_obj_set_style_pad_all(tab_intercom, 4, 0);

        lbl_intercom_status = lv_label_create(tab_intercom);
        lv_label_set_text(lbl_intercom_status, "Đàm thoại: Sẵn sàng");
        lv_obj_set_style_text_font(lbl_intercom_status, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_intercom_status, lv_color_hex(0x10B981), 0);
        lv_obj_align(lbl_intercom_status, LV_ALIGN_TOP_MID, 0, 2);

        const char* room_names[] = {"Phòng 1", "Phòng 2", "Phòng 3", "Phòng 4"};
        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = lv_btn_create(tab_intercom);
            lv_obj_set_size(btn_rooms[i], 108, 34);
            int x = (i % 2 == 0) ? 4 : 120;
            int y = 20 + (i / 2) * 38;
            lv_obj_set_pos(btn_rooms[i], x, y);
            lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x1F2937), 0);
            lv_obj_set_style_radius(btn_rooms[i], 8, 0);
            lv_obj_add_event_cb(btn_rooms[i], event_handler_trampoline, LV_EVENT_CLICKED, this);

            lbl_rooms[i] = lv_label_create(btn_rooms[i]);
            lv_label_set_text(lbl_rooms[i], room_names[i]);
            lv_obj_set_style_text_font(lbl_rooms[i], &font_vietnamese_14, 0);
            lv_obj_center(lbl_rooms[i]);
        }

        btn_broadcast = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_broadcast, 224, 34);
        lv_obj_align(btn_broadcast, LV_ALIGN_TOP_MID, 0, 100);
        lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x2563EB), 0);
        lv_obj_set_style_radius(btn_broadcast, 8, 0);
        lv_obj_add_event_cb(btn_broadcast, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lv_obj_t* lbl_all = lv_label_create(btn_broadcast);
        lv_label_set_text(lbl_all, "GỌI TOÀN NHÀ (ALL)");
        lv_obj_set_style_text_font(lbl_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_all);

        btn_intercom_ptt = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_intercom_ptt, 224, 46);
        lv_obj_align(btn_intercom_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x059669), 0);
        lv_obj_set_style_radius(btn_intercom_ptt, 10, 0);
        lv_obj_add_event_cb(btn_intercom_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_intercom_ptt = lv_label_create(btn_intercom_ptt);
        lv_label_set_text(lbl_intercom_ptt, "NHẤN GIỮ ĐỂ NÓI");
        lv_obj_set_style_text_font(lbl_intercom_ptt, &font_vietnamese_14, 0);
        lv_obj_center(lbl_intercom_ptt);
    }

    void build_tab_settings(uint8_t init_vol, uint8_t init_bright) {
        lv_obj_clear_flag(tab_settings, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_settings, lv_color_hex(0x0B0F19), 0);
        lv_obj_set_style_pad_all(tab_settings, 5, 0);

        // 1. Âm lượng Loa (Y: 0..24)
        lv_obj_t* lbl_vol = lv_label_create(tab_settings);
        lv_label_set_text(lbl_vol, "Âm Lượng:");
        lv_obj_set_style_text_font(lbl_vol, &font_vietnamese_14, 0);
        lv_obj_align(lbl_vol, LV_ALIGN_TOP_LEFT, 4, 0);

        lbl_vol_val = lv_label_create(tab_settings);
        lv_label_set_text_fmt(lbl_vol_val, "%d%%", init_vol);
        lv_obj_set_style_text_color(lbl_vol_val, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_vol_val, &font_vietnamese_14, 0);
        lv_obj_align(lbl_vol_val, LV_ALIGN_TOP_RIGHT, -4, 0);

        slider_vol = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_vol, 224, 8);
        lv_obj_align(slider_vol, LV_ALIGN_TOP_MID, 0, 18);
        lv_slider_set_range(slider_vol, 0, 100);
        lv_slider_set_value(slider_vol, init_vol, LV_ANIM_OFF);
        lv_obj_add_event_cb(slider_vol, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        // 2. Độ sáng Màn hình (Y: 30..54)
        lv_obj_t* lbl_br = lv_label_create(tab_settings);
        lv_label_set_text(lbl_br, "Độ Sáng:");
        lv_obj_set_style_text_font(lbl_br, &font_vietnamese_14, 0);
        lv_obj_align(lbl_br, LV_ALIGN_TOP_LEFT, 4, 30);

        lbl_bright_val = lv_label_create(tab_settings);
        lv_label_set_text_fmt(lbl_bright_val, "%d", init_bright);
        lv_obj_set_style_text_color(lbl_bright_val, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_bright_val, &font_vietnamese_14, 0);
        lv_obj_align(lbl_bright_val, LV_ALIGN_TOP_RIGHT, -4, 30);

        slider_bright = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_bright, 224, 8);
        lv_obj_align(slider_bright, LV_ALIGN_TOP_MID, 0, 48);
        lv_slider_set_range(slider_bright, 20, 255);
        lv_slider_set_value(slider_bright, init_bright, LV_ANIM_OFF);
        lv_obj_add_event_cb(slider_bright, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        // 3. Grid 4 Nút Chẩn Đoán & Tiện Ích (Y: 64..138)
        // Hàng 1 (Y: 64): Test Loa & Test Mic
        btn_test_speaker = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_speaker, 108, 34);
        lv_obj_set_pos(btn_test_speaker, 4, 64);
        lv_obj_set_style_bg_color(btn_test_speaker, lv_color_hex(0x1E3A8A), 0);
        lv_obj_set_style_radius(btn_test_speaker, 7, 0);
        lv_obj_add_event_cb(btn_test_speaker, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ts = lv_label_create(btn_test_speaker);
        lv_label_set_text(lbl_ts, "🔊 TEST LOA");
        lv_obj_set_style_text_font(lbl_ts, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ts);

        btn_test_mic = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_mic, 108, 34);
        lv_obj_set_pos(btn_test_mic, 120, 64);
        lv_obj_set_style_bg_color(btn_test_mic, lv_color_hex(0x065F46), 0);
        lv_obj_set_style_radius(btn_test_mic, 7, 0);
        lv_obj_add_event_cb(btn_test_mic, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tm = lv_label_create(btn_test_mic);
        lv_label_set_text(lbl_tm, "🎙️ TEST MIC");
        lv_obj_set_style_text_font(lbl_tm, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tm);

        // Hàng 2 (Y: 104): Test Server & Đổi WiFi
        btn_test_ws = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_ws, 108, 34);
        lv_obj_set_pos(btn_test_ws, 4, 104);
        lv_obj_set_style_bg_color(btn_test_ws, lv_color_hex(0x581C87), 0);
        lv_obj_set_style_radius(btn_test_ws, 7, 0);
        lv_obj_add_event_cb(btn_test_ws, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tw = lv_label_create(btn_test_ws);
        lv_label_set_text(lbl_tw, "📡 TEST SERVER");
        lv_obj_set_style_text_font(lbl_tw, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tw);

        btn_enter_ap = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_enter_ap, 108, 34);
        lv_obj_set_pos(btn_enter_ap, 120, 104);
        lv_obj_set_style_bg_color(btn_enter_ap, lv_color_hex(0x92400E), 0);
        lv_obj_set_style_radius(btn_enter_ap, 7, 0);
        lv_obj_add_event_cb(btn_enter_ap, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ap = lv_label_create(btn_enter_ap);
        lv_label_set_text(lbl_ap, "⚙️ ĐỔI WIFI");
        lv_obj_set_style_text_font(lbl_ap, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ap);

        // 4. Khung Hiển Thị Kết Quả Chẩn Đoán (Y: 144)
        lv_obj_t* box_diag = lv_obj_create(tab_settings);
        lv_obj_set_size(box_diag, 224, 46);
        lv_obj_set_pos(box_diag, 4, 144);
        lv_obj_set_style_bg_color(box_diag, lv_color_hex(0x111827), 0);
        lv_obj_set_style_border_color(box_diag, lv_color_hex(0x1F2937), 0);
        lv_obj_set_style_radius(box_diag, 8, 0);
        lv_obj_set_style_pad_all(box_diag, 4, 0);
        lv_obj_clear_flag(box_diag, LV_OBJ_FLAG_SCROLLABLE);

        lbl_diag_result = lv_label_create(box_diag);
        lv_label_set_text(lbl_diag_result, "Chẩn đoán: Sẵn sàng kiểm tra");
        lv_obj_set_style_text_color(lbl_diag_result, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_diag_result, &font_vietnamese_14, 0);
        lv_obj_center(lbl_diag_result);

        // 5. Ghi chú chân trang (Y: 196)
        lbl_net_info = lv_label_create(tab_settings);
        lv_label_set_text(lbl_net_info, "Nhấn nút để kiểm tra phần cứng & server.\nChạm giữ Header 2s để vào Soft-AP.");
        lv_obj_set_style_text_color(lbl_net_info, lv_color_hex(0x6B7280), 0);
        lv_obj_set_style_text_font(lbl_net_info, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_net_info, 4, 196);
    }
};

extern UILVGLDashboard uiDashboard;
