#pragma once
#include <Arduino.h>
#include <lvgl.h>
#include <ArduinoJson.h>
#include "font_vietnamese.h"

#define MAX_LOCAL_BUTTONS 12
#define MAX_ROOM_CHIPS 16
#define MAX_REMOTE_BUTTONS 16
#define MAX_ROOM_DEVICES 8

typedef void (*UIActionCallback_t)(const char* target, const char* action, int value);

static inline String utf8_safe_substring(const String& str, size_t max_chars) {
    if (str.length() == 0 || max_chars == 0) return "";
    const char* s = str.c_str();
    size_t char_count = 0;
    size_t byte_idx = 0;
    size_t total_bytes = str.length();

    while (byte_idx < total_bytes && char_count < max_chars) {
        uint8_t c = (uint8_t)s[byte_idx];
        size_t char_len = 1;
        if ((c & 0x80) == 0) char_len = 1;
        else if ((c & 0xE0) == 0xC0) char_len = 2;
        else if ((c & 0xF0) == 0xE0) char_len = 3;
        else if ((c & 0xF8) == 0xF0) char_len = 4;
        
        if (byte_idx + char_len > total_bytes) break;
        byte_idx += char_len;
        char_count++;
    }
    return str.substring(0, byte_idx);
}

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

struct UIRoomDevice {
    char name[32];
    char entity_id[48];
    char icon[16];
    bool is_on = false;
    float temp = 26.0f;
};

struct UIRoomInfo {
    char name[48];
    uint8_t active_count;
    uint8_t total_count;
    uint8_t device_count;
    UIRoomDevice devices[MAX_ROOM_DEVICES];
};

class UILVGLDashboard {
public:
    enum UIDashboardViewMode {
        VIEW_MODE_LOCAL = 0,
        VIEW_MODE_ALL_ROOMS,
        VIEW_MODE_REMOTE_ROOM
    };

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

    // View State & Timeout
    UIDashboardViewMode view_mode;
    uint8_t room_view_timeout_sec;
    unsigned long last_interaction_ms;
    int selected_remote_room_idx;
    String selected_remote_room;
    String local_room_name;

    UIRoomInfo house_rooms[MAX_ROOM_CHIPS];
    uint8_t active_rooms_count;
    uint8_t total_house_active_devices;

    // Tab 0 Elements: Thiet Bi
    UIButtonSlot local_buttons[MAX_LOCAL_BUTTONS];
    uint8_t local_buttons_count;

    UIButtonSlot remote_buttons[MAX_REMOTE_BUTTONS];
    uint8_t remote_buttons_count;

    UIButtonSlot* active_climate_slot;

    // Top Navigation Bar (y = 2, h = 32)
    lv_obj_t* cont_top_nav;
    lv_obj_t* btn_toan_nha;
    lv_obj_t* lbl_toan_nha;
    lv_obj_t* btn_master_off;
    lv_obj_t* lbl_master_off;
    lv_obj_t* lbl_nav_title;
    lv_obj_t* btn_nav_back_rooms;
    lv_obj_t* lbl_nav_back_rooms;
    lv_obj_t* btn_nav_back_local;
    lv_obj_t* lbl_nav_back_local;

    // 2-Column Content Area (y = 36, h = 206)
    lv_obj_t* cont_devices_scroll;

    // Room Cards
    lv_obj_t* btn_room_cards[MAX_ROOM_CHIPS];
    lv_obj_t* lbl_room_cards[MAX_ROOM_CHIPS];

    // Tab 1 Elements: Nala AI
    lv_obj_t* lbl_ai_state;
    lv_obj_t* ai_pulse_circle;
    lv_obj_t* ta_ai_response;
    lv_obj_t* btn_ai_ptt;
    lv_obj_t* lbl_ai_ptt_text;

    // Tab 2 Elements: Dam Thoai
    struct IntercomTarget {
        uint8_t id;
        char name[32];
        char floor[16];
        bool is_online;
    };
    IntercomTarget intercom_targets[4];
    uint8_t active_intercom_targets_count;

    lv_obj_t* btn_broadcast;
    lv_obj_t* btn_rooms[4];
    lv_obj_t* lbl_rooms[4];
    lv_obj_t* btn_intercom_ptt;
    lv_obj_t* lbl_intercom_ptt;
    lv_obj_t* lbl_intercom_status;
    uint8_t selected_room_idx;

    // Tab 3 Elements: Cai Dat
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
    lv_obj_t* lbl_diag_result;
    lv_obj_t* lbl_firmware_ver;
    lv_obj_t* lbl_net_info;
    bool ring_on_call_enabled;

    // Incoming Call Modal
    lv_obj_t* modal_incoming_call;
    lv_obj_t* lbl_incoming_title;
    lv_obj_t* lbl_incoming_caller;
    lv_obj_t* lbl_incoming_status;
    lv_obj_t* btn_incoming_accept;
    lv_obj_t* btn_incoming_reject;

    // Fullscreen Climate Modal Dialog
    lv_obj_t* dialog_climate;
    lv_obj_t* lbl_clim_title;
    lv_obj_t* lbl_clim_temp;
    lv_obj_t* lbl_clim_status;
    lv_obj_t* btn_clim_minus;
    lv_obj_t* btn_clim_plus;
    lv_obj_t* btn_clim_power;
    lv_obj_t* lbl_clim_power;
    lv_obj_t* btn_clim_fan;
    lv_obj_t* lbl_clim_fan;
    lv_obj_t* btn_clim_swing;
    lv_obj_t* lbl_clim_swing;
    lv_obj_t* btn_clim_modes[4];
    lv_obj_t* btn_clim_eco26;
    lv_obj_t* lbl_clim_modes;
    lv_obj_t* lbl_clim_info;
    lv_obj_t* btn_clim_close;

    bool pending_climate_flush = false;
    unsigned long pending_climate_flush_ms = 0;
    float pending_climate_target_temp = 26.0f;

    UIActionCallback_t action_cb = nullptr;

    static void event_handler_trampoline(lv_event_t* e) {
        UILVGLDashboard* instance = (UILVGLDashboard*)lv_event_get_user_data(e);
        if (instance) instance->handle_event(e);
    }

public:
    UILVGLDashboard()
        : tabview(nullptr), tab_devices(nullptr), tab_ai(nullptr), tab_intercom(nullptr), tab_settings(nullptr),
          header_obj(nullptr), lbl_header_title(nullptr), lbl_header_info(nullptr), lbl_ws_status(nullptr),
          view_mode(VIEW_MODE_LOCAL), room_view_timeout_sec(15), last_interaction_ms(0),
          selected_remote_room_idx(-1), selected_remote_room(""), local_room_name("Phong Khach"),
          active_rooms_count(0), total_house_active_devices(0),
          local_buttons_count(0), remote_buttons_count(0), active_climate_slot(nullptr),
          cont_top_nav(nullptr), btn_toan_nha(nullptr), lbl_toan_nha(nullptr),
          btn_master_off(nullptr), lbl_master_off(nullptr),
          lbl_nav_title(nullptr), btn_nav_back_rooms(nullptr), lbl_nav_back_rooms(nullptr),
          btn_nav_back_local(nullptr), lbl_nav_back_local(nullptr),
          cont_devices_scroll(nullptr),
          lbl_ai_state(nullptr), ai_pulse_circle(nullptr), ta_ai_response(nullptr), btn_ai_ptt(nullptr), lbl_ai_ptt_text(nullptr),
          active_intercom_targets_count(0),
          btn_broadcast(nullptr), btn_intercom_ptt(nullptr), lbl_intercom_ptt(nullptr),
          lbl_intercom_status(nullptr), selected_room_idx(0xFF),
          slider_vol(nullptr), lbl_vol_val(nullptr), slider_bright(nullptr), lbl_bright_val(nullptr),
          slider_mic(nullptr), lbl_mic_val(nullptr),
          btn_enter_ap(nullptr), btn_test_speaker(nullptr), btn_test_mic(nullptr), btn_test_ws(nullptr),
          lbl_diag_result(nullptr), btn_check_ota(nullptr), btn_toggle_ring(nullptr), lbl_toggle_ring(nullptr),
          lbl_firmware_ver(nullptr), lbl_net_info(nullptr), ring_on_call_enabled(true),
          modal_incoming_call(nullptr), lbl_incoming_title(nullptr), lbl_incoming_caller(nullptr), lbl_incoming_status(nullptr),
          btn_incoming_accept(nullptr), btn_incoming_reject(nullptr),
          dialog_climate(nullptr), lbl_clim_title(nullptr), lbl_clim_temp(nullptr), lbl_clim_status(nullptr),
          btn_clim_minus(nullptr), btn_clim_plus(nullptr), btn_clim_power(nullptr), lbl_clim_power(nullptr),
          btn_clim_fan(nullptr), lbl_clim_fan(nullptr), btn_clim_swing(nullptr), lbl_clim_swing(nullptr),
          btn_clim_eco26(nullptr), lbl_clim_modes(nullptr), lbl_clim_info(nullptr), btn_clim_close(nullptr)
    {
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            btn_room_cards[i] = nullptr;
            lbl_room_cards[i] = nullptr;
        }
        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = nullptr;
            lbl_rooms[i] = nullptr;
            btn_clim_modes[i] = nullptr;
        }
    }

    void set_action_callback(UIActionCallback_t cb) {
        action_cb = cb;
    }

    void set_room_view_timeout(uint8_t sec) {
        if (sec >= 5 && sec <= 120) {
            room_view_timeout_sec = sec;
            Serial.printf("[UI] Updated room view timeout: %ds\n", sec);
        }
    }

    void check_flush_climate_setpoint() {
        if (pending_climate_flush && millis() - pending_climate_flush_ms >= 800) {
            pending_climate_flush = false;
            if (active_climate_slot && action_cb) {
                action_cb("climate_set_temp", active_climate_slot->entity_id.c_str(), (int)(pending_climate_target_temp * 10));
            }
        }
    }

    void check_navigation_timeout() {
        if (view_mode == VIEW_MODE_ALL_ROOMS || view_mode == VIEW_MODE_REMOTE_ROOM) {
            if (millis() - last_interaction_ms >= (unsigned long)room_view_timeout_sec * 1000UL) {
                Serial.printf("[UI-TIMEOUT] %ds elapsed -> Auto return to LOCAL view\n", room_view_timeout_sec);
                switch_view_mode(VIEW_MODE_LOCAL);
            }
        }
    }

    void init(const char* room_name, const char* ip_str, const char* pair_code, 
              uint8_t init_vol, uint8_t init_bright, bool init_ring_on_call = true, uint8_t init_mic_gain = 5,
              uint8_t init_room_view_timeout = 15) {
        ring_on_call_enabled = init_ring_on_call;
        room_view_timeout_sec = init_room_view_timeout;
        local_room_name = (room_name && strlen(room_name) > 0) ? room_name : "Phong Khach";
        lv_obj_t* scr = lv_scr_act();
        lv_obj_clear_flag(scr, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(scr, lv_color_hex(0x080C14), 0);

        // Header tren cung (Cao 38px, rong 240px)
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
        lv_label_set_text_fmt(lbl_header_title, "NALA: %s", room_name && strlen(room_name) > 0 ? room_name : "Thiet Bi");
        lv_obj_set_style_text_color(lbl_header_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_header_title, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_title, LV_ALIGN_TOP_LEFT, 4, -1);

        lbl_ws_status = lv_label_create(header_obj);
        lv_label_set_text(lbl_ws_status, "Offline");
        lv_obj_set_style_text_color(lbl_ws_status, lv_color_hex(0xEF4444), 0);
        lv_obj_set_style_text_font(lbl_ws_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_ws_status, LV_ALIGN_TOP_RIGHT, -4, -1);

        lbl_header_info = lv_label_create(header_obj);
        lv_label_set_text_fmt(lbl_header_info, "IP: %s | Ma: [%s]", ip_str ? ip_str : "192.168.1.x", pair_code ? pair_code : "881C");
        lv_obj_set_style_text_color(lbl_header_info, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_header_info, &font_vietnamese_14, 0);
        lv_obj_align(lbl_header_info, LV_ALIGN_BOTTOM_LEFT, 4, 1);

        // TabView (Duoi Header, Cao 282px, Rong 240px, 4 Tab day)
        tabview = lv_tabview_create(scr, LV_DIR_BOTTOM, 36);
        lv_obj_clear_flag(lv_tabview_get_content(tabview), LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_size(tabview, 240, 282);
        lv_obj_align(tabview, LV_ALIGN_BOTTOM_MID, 0, 0);
        lv_obj_set_style_bg_color(tabview, lv_color_hex(0x080C14), 0);

        lv_obj_t* tab_btns = lv_tabview_get_tab_btns(tabview);
        lv_obj_set_style_bg_color(tab_btns, lv_color_hex(0x0F172A), 0);
        lv_obj_set_style_text_color(tab_btns, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(tab_btns, &font_vietnamese_14, 0);

        // 4 Tab doc lap
        tab_devices = lv_tabview_add_tab(tabview, "Thiet Bi");
        tab_ai = lv_tabview_add_tab(tabview, "Nala AI");
        tab_intercom = lv_tabview_add_tab(tabview, "Dam Thoai");
        tab_settings = lv_tabview_add_tab(tabview, "Cai Dat");

        build_tab_devices();
        build_tab_ai();
        build_tab_intercom();
        build_tab_settings(init_vol, init_bright, init_mic_gain);

        build_incoming_call_modal(scr);
        build_climate_dialog(scr);

        // Mac dinh khoi dong vao Che do Phong Hien Tai
        switch_view_mode(VIEW_MODE_LOCAL);
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
            snprintf(buf, sizeof(buf), "Ban: %s | PSRAM: %.1fMB", ver_str, psram_mb);
            lv_label_set_text(lbl_firmware_ver, buf);
        }
    }

    void set_diag_result(const char* text, uint32_t color_hex) {
        if (lbl_diag_result && text) {
            lv_label_set_text(lbl_diag_result, text);
            lv_obj_set_style_text_color(lbl_diag_result, lv_color_hex(color_hex), 0);
        }
    }

    void set_room_title(const char* new_room) {
        if (!new_room || strlen(new_room) == 0) return;
        local_room_name = new_room;
        if (view_mode == VIEW_MODE_LOCAL && lbl_header_title) {
            lv_label_set_text_fmt(lbl_header_title, "NALA: %s", local_room_name.c_str());
        }
    }

    void sync_buttons(const JsonArrayConst& btn_array) {
        uint8_t count = btn_array.size();
        if (count > MAX_LOCAL_BUTTONS) count = MAX_LOCAL_BUTTONS;
        local_buttons_count = count;
        Serial.printf("[UI] sync_buttons: Loaded %d local buttons\n", count);

        for (uint8_t i = 0; i < count; i++) {
            local_buttons[i].id = btn_array[i]["id"] | String("btn_" + String(i + 1));
            local_buttons[i].name = btn_array[i]["name"] | String("Nut " + String(i + 1));
            local_buttons[i].entity_id = btn_array[i]["entity_id"] | "";
            local_buttons[i].icon = btn_array[i]["icon"] | "light";
            local_buttons[i].room = btn_array[i]["room"] | local_room_name;

            bool is_on = btn_array[i]["is_on"] | false;
            if (!is_on && btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                is_on = (st == "on" || (st != "off" && st != "unavailable" && st != "unknown" && st.length() > 0));
            }
            local_buttons[i].is_on = is_on;

            if (btn_array[i].containsKey("attributes")) {
                JsonObjectConst attrs = btn_array[i]["attributes"];
                if (attrs.containsKey("temperature")) {
                    local_buttons[i].temperature = attrs["temperature"] | 26.0f;
                }
                if (attrs.containsKey("current_temperature")) {
                    local_buttons[i].current_temperature = attrs["current_temperature"] | 28.0f;
                }
                if (attrs.containsKey("hvac_mode")) {
                    local_buttons[i].hvac_mode = attrs["hvac_mode"] | "off";
                }
                if (attrs.containsKey("fan_mode")) {
                    local_buttons[i].fan_mode = attrs["fan_mode"] | "auto";
                }
                if (attrs.containsKey("swing_mode")) {
                    String sm = attrs["swing_mode"] | "";
                    local_buttons[i].swing_on = (sm != "off" && sm.length() > 0);
                }
            }
            if (btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                local_buttons[i].hvac_mode = st;
            }
            update_slot_ui(local_buttons[i]);
        }

        if (view_mode == VIEW_MODE_LOCAL) {
            switch_view_mode(VIEW_MODE_LOCAL);
        }
    }

    void sync_house_status(const JsonObjectConst& house_st) {
        int on_devs = house_st["total_on_devices"] | (house_st["total_on_lights"] | 0);
        total_house_active_devices = on_devs;
        update_toan_nha_button_ui();
    }

    void sync_all_rooms(const JsonArrayConst& rooms_array) {
        active_rooms_count = 0;
        int house_active = 0;

        for (JsonObjectConst r : rooms_array) {
            if (active_rooms_count >= MAX_ROOM_CHIPS) break;
            const char* rname = r["room_name"] | "";
            if (rname && strlen(rname) > 0) {
                int idx = active_rooms_count;
                strncpy(house_rooms[idx].name, rname, sizeof(house_rooms[0].name) - 1);
                house_rooms[idx].name[sizeof(house_rooms[0].name) - 1] = '\0';
                int act = r["active_devices_count"] | r["active_count"] | 0;
                house_rooms[idx].active_count = act;
                house_rooms[idx].total_count = r["total_devices_count"] | r["total_count"] | 0;
                house_active += act;

                house_rooms[idx].device_count = 0;
                if (r.containsKey("buttons")) {
                    JsonArrayConst r_btns = r["buttons"];
                    for (JsonObjectConst rb : r_btns) {
                        if (house_rooms[idx].device_count >= MAX_ROOM_DEVICES) break;
                        const char* eid = rb["entity_id"] | "";
                        if (!eid || strlen(eid) == 0) continue;
                        int d_idx = house_rooms[idx].device_count++;
                        const char* dname = rb["name"] | eid;
                        strncpy(house_rooms[idx].devices[d_idx].name, dname, sizeof(house_rooms[0].devices[0].name) - 1);
                        house_rooms[idx].devices[d_idx].name[sizeof(house_rooms[0].devices[0].name) - 1] = '\0';
                        strncpy(house_rooms[idx].devices[d_idx].entity_id, eid, sizeof(house_rooms[0].devices[0].entity_id) - 1);
                        house_rooms[idx].devices[d_idx].entity_id[sizeof(house_rooms[0].devices[0].entity_id) - 1] = '\0';
                        const char* ic = rb["icon"] | "light";
                        strncpy(house_rooms[idx].devices[d_idx].icon, ic, sizeof(house_rooms[0].devices[0].icon) - 1);
                        house_rooms[idx].devices[d_idx].icon[sizeof(house_rooms[0].devices[0].icon) - 1] = '\0';
                        house_rooms[idx].devices[d_idx].is_on = rb["is_on"] | false;
                        house_rooms[idx].devices[d_idx].temp = rb["attributes"]["temperature"] | 26.0f;
                    }
                }
                active_rooms_count++;
            }
        }

        total_house_active_devices = house_active;
        update_toan_nha_button_ui();
        update_room_cards_ui();

        if (view_mode == VIEW_MODE_ALL_ROOMS) {
            switch_view_mode(VIEW_MODE_ALL_ROOMS);
        } else if (view_mode == VIEW_MODE_REMOTE_ROOM && selected_remote_room_idx >= 0) {
            switch_view_mode(VIEW_MODE_REMOTE_ROOM, selected_remote_room_idx);
        }
    }

    void update_toan_nha_button_ui() {
        if (!btn_toan_nha || !lbl_toan_nha) return;
        char buf[48];
        if (total_house_active_devices > 0) {
            snprintf(buf, sizeof(buf), "TOAN NHA (%d)", total_house_active_devices);
            lv_label_set_text(lbl_toan_nha, buf);
            lv_obj_set_style_bg_color(btn_toan_nha, lv_color_hex(0x854D0E), 0);
            lv_obj_set_style_border_color(btn_toan_nha, lv_color_hex(0xF59E0B), 0);
            lv_obj_set_style_border_width(btn_toan_nha, 2, 0);
            lv_obj_set_style_text_color(lbl_toan_nha, lv_color_hex(0xFEF08A), 0);
            if (btn_master_off && view_mode == VIEW_MODE_LOCAL) {
                lv_obj_clear_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
            }
        } else {
            lv_label_set_text(lbl_toan_nha, "TOAN NHA");
            lv_obj_set_style_bg_color(btn_toan_nha, lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(btn_toan_nha, lv_color_hex(0x38BDF8), 0);
            lv_obj_set_style_border_width(btn_toan_nha, 1, 0);
            lv_obj_set_style_text_color(lbl_toan_nha, lv_color_hex(0x38BDF8), 0);
            if (btn_master_off) {
                lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    void update_room_cards_ui() {
        for (int i = 0; i < active_rooms_count; i++) {
            if (!btn_room_cards[i] || !lbl_room_cards[i]) continue;
            String rname = utf8_safe_substring(String(house_rooms[i].name), 12);
            char buf[64];
            if (house_rooms[i].active_count > 0) {
                snprintf(buf, sizeof(buf), "%s\n%d BAT", rname.c_str(), house_rooms[i].active_count);
                lv_obj_set_style_bg_color(btn_room_cards[i], lv_color_hex(0x854D0E), 0);
                lv_obj_set_style_border_color(btn_room_cards[i], lv_color_hex(0xF59E0B), 0);
                lv_obj_set_style_border_width(btn_room_cards[i], 2, 0);
                lv_obj_set_style_text_color(lbl_room_cards[i], lv_color_hex(0xFEF08A), 0);
            } else {
                snprintf(buf, sizeof(buf), "%s\nTat het", rname.c_str());
                lv_obj_set_style_bg_color(btn_room_cards[i], lv_color_hex(0x1E293B), 0);
                lv_obj_set_style_border_color(btn_room_cards[i], lv_color_hex(0x334155), 0);
                lv_obj_set_style_border_width(btn_room_cards[i], 1, 0);
                lv_obj_set_style_text_color(lbl_room_cards[i], lv_color_hex(0x94A3B8), 0);
            }
            lv_label_set_text(lbl_room_cards[i], buf);
        }
    }

    void load_remote_room_devices(int room_idx) {
        if (room_idx < 0 || room_idx >= active_rooms_count) return;
        selected_remote_room_idx = room_idx;
        selected_remote_room = house_rooms[room_idx].name;
        remote_buttons_count = house_rooms[room_idx].device_count;
        if (remote_buttons_count > MAX_REMOTE_BUTTONS) remote_buttons_count = MAX_REMOTE_BUTTONS;

        for (int i = 0; i < remote_buttons_count; i++) {
            const UIRoomDevice& d = house_rooms[room_idx].devices[i];
            remote_buttons[i].id = String(d.entity_id);
            remote_buttons[i].name = String(d.name);
            remote_buttons[i].entity_id = String(d.entity_id);
            remote_buttons[i].icon = String(d.icon);
            remote_buttons[i].room = String(house_rooms[room_idx].name);
            remote_buttons[i].is_on = d.is_on;
            remote_buttons[i].temperature = d.temp > 10.0f ? d.temp : 26.0f;
            update_slot_ui(remote_buttons[i]);
        }
    }

    UIDashboardViewMode pending_view_mode = VIEW_MODE_LOCAL;
    int pending_remote_room_idx = -1;

    static void async_view_mode_cb(void* user_data) {
        UILVGLDashboard* self = (UILVGLDashboard*)user_data;
        if (self) {
            self->switch_view_mode(self->pending_view_mode, self->pending_remote_room_idx);
        }
    }

    void request_view_mode(UIDashboardViewMode mode, int remote_idx = -1) {
        pending_view_mode = mode;
        pending_remote_room_idx = remote_idx;
        lv_async_call(async_view_mode_cb, this);
    }

    void switch_view_mode(UIDashboardViewMode mode, int remote_room_idx = -1) {
        view_mode = mode;
        last_interaction_ms = millis();

        if (mode == VIEW_MODE_LOCAL) {
            // Header Title
            if (lbl_header_title) {
                lv_label_set_text_fmt(lbl_header_title, "NALA: %s", local_room_name.c_str());
            }

            // Top Navigation Bar
            if (btn_toan_nha) lv_obj_clear_flag(btn_toan_nha, LV_OBJ_FLAG_HIDDEN);
            if (lbl_nav_title) lv_obj_add_flag(lbl_nav_title, LV_OBJ_FLAG_HIDDEN);
            if (btn_nav_back_rooms) lv_obj_add_flag(btn_nav_back_rooms, LV_OBJ_FLAG_HIDDEN);
            if (btn_nav_back_local) lv_obj_add_flag(btn_nav_back_local, LV_OBJ_FLAG_HIDDEN);
            update_toan_nha_button_ui();

            // Hide Room Cards
            for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
                if (btn_room_cards[i]) lv_obj_add_flag(btn_room_cards[i], LV_OBJ_FLAG_HIDDEN);
            }

            // Hide Remote Buttons
            for (int i = 0; i < MAX_REMOTE_BUTTONS; i++) {
                if (remote_buttons[i].btn_obj) lv_obj_add_flag(remote_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }

            if (cont_devices_scroll) {
                if (local_buttons_count > 8) {
                    lv_obj_add_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                } else {
                    lv_obj_clear_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                }
                lv_obj_scroll_to_y(cont_devices_scroll, 0, LV_ANIM_OFF);
            }

            // Show Local Buttons
            for (int i = 0; i < local_buttons_count; i++) {
                if (!local_buttons[i].btn_obj) continue;
                lv_obj_clear_flag(local_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                int x = (i % 2 == 0) ? 2 : 120;
                int y = (i / 2) * 50;
                lv_obj_set_pos(local_buttons[i].btn_obj, x, y);
                update_slot_ui(local_buttons[i]);
            }
            for (int i = local_buttons_count; i < MAX_LOCAL_BUTTONS; i++) {
                if (local_buttons[i].btn_obj) lv_obj_add_flag(local_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
        }
        else if (mode == VIEW_MODE_ALL_ROOMS) {
            // Header Title
            if (lbl_header_title) {
                lv_label_set_text(lbl_header_title, "NALA: TOAN NHA");
            }

            // Top Navigation Bar
            if (btn_toan_nha) lv_obj_add_flag(btn_toan_nha, LV_OBJ_FLAG_HIDDEN);
            if (btn_master_off) lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
            if (btn_nav_back_rooms) lv_obj_add_flag(btn_nav_back_rooms, LV_OBJ_FLAG_HIDDEN);
            if (lbl_nav_title) {
                lv_label_set_text(lbl_nav_title, "CAC PHONG");
                lv_obj_clear_flag(lbl_nav_title, LV_OBJ_FLAG_HIDDEN);
            }
            if (btn_nav_back_local) {
                lv_obj_clear_flag(btn_nav_back_local, LV_OBJ_FLAG_HIDDEN);
                if (lbl_nav_back_local) lv_label_set_text(lbl_nav_back_local, "VE PHONG");
            }

            // Hide Local Buttons
            for (int i = 0; i < MAX_LOCAL_BUTTONS; i++) {
                if (local_buttons[i].btn_obj) lv_obj_add_flag(local_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }

            // Hide Remote Buttons
            for (int i = 0; i < MAX_REMOTE_BUTTONS; i++) {
                if (remote_buttons[i].btn_obj) lv_obj_add_flag(remote_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }

            if (cont_devices_scroll) {
                if (active_rooms_count > 8) {
                    lv_obj_add_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                } else {
                    lv_obj_clear_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                }
                lv_obj_scroll_to_y(cont_devices_scroll, 0, LV_ANIM_OFF);
            }

            // Show Room Cards
            update_room_cards_ui();
            for (int i = 0; i < active_rooms_count; i++) {
                if (!btn_room_cards[i]) continue;
                lv_obj_clear_flag(btn_room_cards[i], LV_OBJ_FLAG_HIDDEN);
                int x = (i % 2 == 0) ? 2 : 120;
                int y = (i / 2) * 50;
                lv_obj_set_pos(btn_room_cards[i], x, y);
            }
            for (int i = active_rooms_count; i < MAX_ROOM_CHIPS; i++) {
                if (btn_room_cards[i]) lv_obj_add_flag(btn_room_cards[i], LV_OBJ_FLAG_HIDDEN);
            }
        }
        else if (mode == VIEW_MODE_REMOTE_ROOM) {
            // Header Title
            if (lbl_header_title) {
                lv_label_set_text_fmt(lbl_header_title, "NALA: %s", selected_remote_room.c_str());
            }

            // Top Navigation Bar
            if (btn_toan_nha) lv_obj_add_flag(btn_toan_nha, LV_OBJ_FLAG_HIDDEN);
            if (btn_master_off) lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
            if (lbl_nav_title) {
                char buf[48];
                snprintf(buf, sizeof(buf), "Xem: %s", selected_remote_room.c_str());
                lv_label_set_text(lbl_nav_title, buf);
                lv_obj_clear_flag(lbl_nav_title, LV_OBJ_FLAG_HIDDEN);
            }
            if (btn_nav_back_rooms) lv_obj_clear_flag(btn_nav_back_rooms, LV_OBJ_FLAG_HIDDEN);
            if (btn_nav_back_local) {
                lv_obj_clear_flag(btn_nav_back_local, LV_OBJ_FLAG_HIDDEN);
                if (lbl_nav_back_local) lv_label_set_text(lbl_nav_back_local, "VE PHONG");
            }

            // Hide Local Buttons & Room Cards
            for (int i = 0; i < MAX_LOCAL_BUTTONS; i++) {
                if (local_buttons[i].btn_obj) lv_obj_add_flag(local_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
            for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
                if (btn_room_cards[i]) lv_obj_add_flag(btn_room_cards[i], LV_OBJ_FLAG_HIDDEN);
            }

            if (remote_room_idx >= 0) {
                load_remote_room_devices(remote_room_idx);
            }

            if (cont_devices_scroll) {
                if (remote_buttons_count > 8) {
                    lv_obj_add_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                } else {
                    lv_obj_clear_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
                }
                lv_obj_scroll_to_y(cont_devices_scroll, 0, LV_ANIM_OFF);
            }

            // Show Remote Buttons
            for (int i = 0; i < remote_buttons_count; i++) {
                if (!remote_buttons[i].btn_obj) continue;
                lv_obj_clear_flag(remote_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                int x = (i % 2 == 0) ? 2 : 120;
                int y = (i / 2) * 50;
                lv_obj_set_pos(remote_buttons[i].btn_obj, x, y);
                update_slot_ui(remote_buttons[i]);
            }
            for (int i = remote_buttons_count; i < MAX_REMOTE_BUTTONS; i++) {
                if (remote_buttons[i].btn_obj) lv_obj_add_flag(remote_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            }
        }
    }

    void update_entity_state(const char* entity_id, bool is_on, float temp = 0.0f, float current_temp = 0.0f,
                             const char* hvac = nullptr, const char* fan = nullptr, int swing = -1) {
        if (!entity_id) return;

        // Local buttons
        for (int i = 0; i < local_buttons_count; i++) {
            if (local_buttons[i].entity_id.equalsIgnoreCase(entity_id)) {
                local_buttons[i].is_on = is_on;
                if (temp > 10.0f) local_buttons[i].temperature = temp;
                if (current_temp > 10.0f) local_buttons[i].current_temperature = current_temp;
                if (hvac && strlen(hvac) > 0) local_buttons[i].hvac_mode = hvac;
                if (fan && strlen(fan) > 0) local_buttons[i].fan_mode = fan;
                if (swing >= 0) local_buttons[i].swing_on = (swing == 1);
                update_slot_ui(local_buttons[i]);
                if (active_climate_slot == &local_buttons[i]) {
                    update_climate_dialog_ui();
                }
            }
        }

        // Remote buttons
        for (int i = 0; i < remote_buttons_count; i++) {
            if (remote_buttons[i].entity_id.equalsIgnoreCase(entity_id)) {
                remote_buttons[i].is_on = is_on;
                if (temp > 10.0f) remote_buttons[i].temperature = temp;
                if (current_temp > 10.0f) remote_buttons[i].current_temperature = current_temp;
                if (hvac && strlen(hvac) > 0) remote_buttons[i].hvac_mode = hvac;
                if (fan && strlen(fan) > 0) remote_buttons[i].fan_mode = fan;
                if (swing >= 0) remote_buttons[i].swing_on = (swing == 1);
                update_slot_ui(remote_buttons[i]);
                if (active_climate_slot == &remote_buttons[i]) {
                    update_climate_dialog_ui();
                }
            }
        }

        // House rooms cache
        for (int r = 0; r < active_rooms_count; r++) {
            for (int d = 0; d < house_rooms[r].device_count; d++) {
                if (strcmp(house_rooms[r].devices[d].entity_id, entity_id) == 0) {
                    house_rooms[r].devices[d].is_on = is_on;
                    if (temp > 10.0f) house_rooms[r].devices[d].temp = temp;
                    break;
                }
            }
        }
    }

    void update_slot_ui(UIButtonSlot& b) {
        if (!b.btn_obj || !b.lbl_obj) return;

        bool is_climate = (b.icon == "climate" || b.entity_id.startsWith("climate"));
        String display_name = b.name;
        if (is_climate) {
            if (display_name.indexOf(':') < 0 && (display_name.length() == 0 || display_name.equalsIgnoreCase("climate"))) {
                display_name = "May Lanh";
            }
        }
        display_name = utf8_safe_substring(display_name, 12);

        char btn_text[64];
        if (is_climate) {
            if (b.is_on && b.temperature > 10.0f) {
                snprintf(btn_text, sizeof(btn_text), "%s\n%.1f*C", display_name.c_str(), b.temperature);
            } else {
                snprintf(btn_text, sizeof(btn_text), "%s\nTAT", display_name.c_str());
            }
        } else {
            const char* st_text = b.is_on ? "BAT" : "TAT";
            snprintf(btn_text, sizeof(btn_text), "%s\n%s", display_name.c_str(), st_text);
        }
        lv_label_set_text(b.lbl_obj, btn_text);
        lv_obj_set_style_text_align(b.lbl_obj, LV_TEXT_ALIGN_CENTER, 0);

        if (b.is_on) {
            if (is_climate) {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x065F46), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x10B981), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            } else if (b.icon == "fan" || b.entity_id.startsWith("fan")) {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x0284C7), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x38BDF8), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            } else {
                lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x2563EB), 0);
                lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x60A5FA), 0);
                lv_obj_set_style_border_width(b.btn_obj, 2, 0);
                lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xFFFFFF), 0);
            }
        } else {
            lv_obj_set_style_bg_color(b.btn_obj, lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(b.btn_obj, lv_color_hex(0x475569), 0);
            lv_obj_set_style_border_width(b.btn_obj, 1, 0);
            lv_obj_set_style_text_color(b.lbl_obj, lv_color_hex(0xE2E8F0), 0);
        }
    }

    void set_ai_state(const char* state_str, const char* text_str) {
        if (!lbl_ai_state) return;
        if (strcmp(state_str, "LISTENING") == 0) {
            lv_label_set_text(lbl_ai_state, "AI: Dang nghe...");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0xF59E0B), 0);
        } else if (strcmp(state_str, "PROCESSING") == 0) {
            lv_label_set_text(lbl_ai_state, "AI: Dang suy nghi...");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x3B82F6), 0);
        } else if (strcmp(state_str, "SPEAKING") == 0) {
            lv_label_set_text(lbl_ai_state, "AI: Dang tra loi...");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
        } else {
            lv_label_set_text(lbl_ai_state, "AI: San sang (Cho lenh)");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
        }
        if (text_str && ta_ai_response) {
            lv_textarea_set_text(ta_ai_response, text_str);
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
            const char* name = target["name"] | "Phong";
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
        snprintf(buf, buf_len, "Thiet bi #%d", sender_id);
    }

    void show_incoming_call(const char* caller_name, bool ring) {
        if (!modal_incoming_call) return;
        if (lbl_incoming_caller && caller_name) {
            char buf[64];
            snprintf(buf, sizeof(buf), "Cuoc goi tu: %s", caller_name);
            lv_label_set_text(lbl_incoming_caller, buf);
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
        ring_on_call_enabled = ring;
        if (slider_vol) {
            lv_slider_set_value(slider_vol, vol, LV_ANIM_OFF);
            char buf[16];
            snprintf(buf, sizeof(buf), "%d%%", vol);
            if (lbl_vol_val) lv_label_set_text(lbl_vol_val, buf);
        }
        if (slider_bright) {
            lv_slider_set_value(slider_bright, bright, LV_ANIM_OFF);
            char buf[16];
            snprintf(buf, sizeof(buf), "%d%%", (bright * 100) / 255);
            if (lbl_bright_val) lv_label_set_text(lbl_bright_val, buf);
        }
        if (slider_mic) {
            lv_slider_set_value(slider_mic, mic_gain, LV_ANIM_OFF);
            const char* gain_names[8] = {"", "Thap", "Vua", "Chuan", "Nhay", "Rat nhay", "Cuc nhay", "Toi da"};
            char buf[32];
            snprintf(buf, sizeof(buf), "Muc %d (%s)", mic_gain, (mic_gain >= 1 && mic_gain <= 7) ? gain_names[mic_gain] : "");
            if (lbl_mic_val) lv_label_set_text(lbl_mic_val, buf);
        }
        if (btn_toggle_ring && lbl_toggle_ring) {
            if (ring) {
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x0284C7), 0);
                lv_label_set_text(lbl_toggle_ring, "CHUONG: BAT");
            } else {
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x334155), 0);
                lv_label_set_text(lbl_toggle_ring, "CHUONG: TAT");
            }
        }
    }

    void handle_event(lv_event_t* e) {
        lv_event_code_t code = lv_event_get_code(e);
        lv_obj_t* target = lv_event_get_target(e);
        lv_obj_t* cur_target = lv_event_get_current_target(e);
        Serial.printf("[UI-EVENT] code=%d target=%p cur=%p\n", (int)code, target, cur_target);

        if (target == header_obj && code == LV_EVENT_LONG_PRESSED) {
            if (action_cb) action_cb("system", "enter_ap_mode", 0);
            return;
        }

        // Sliders on Tab Settings
        if (target == slider_vol && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_vol);
            char buf[16];
            snprintf(buf, sizeof(buf), "%d%%", val);
            lv_label_set_text(lbl_vol_val, buf);
            if (action_cb) action_cb("settings_vol", "volume", val);
            return;
        }
        if (target == slider_bright && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_bright);
            char buf[16];
            snprintf(buf, sizeof(buf), "%d%%", (val * 100) / 255);
            lv_label_set_text(lbl_bright_val, buf);
            if (action_cb) action_cb("settings_bright", "brightness", val);
            return;
        }
        if (target == slider_mic && code == LV_EVENT_VALUE_CHANGED) {
            int val = lv_slider_get_value(slider_mic);
            const char* gain_names[8] = {"", "Thap", "Vua", "Chuan", "Nhay", "Rat nhay", "Cuc nhay", "Toi da"};
            char buf[32];
            snprintf(buf, sizeof(buf), "Muc %d (%s)", val, (val >= 1 && val <= 7) ? gain_names[val] : "");
            lv_label_set_text(lbl_mic_val, buf);
            if (action_cb) action_cb("settings_mic", "mic_gain", val);
            return;
        }

        // PTT Events
        if (target == btn_ai_ptt) {
            if (code == LV_EVENT_PRESSED) {
                last_interaction_ms = millis();
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x16A34A), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "DANG THU AM...");
                if (action_cb) action_cb("ai_ptt", "start", 0);
            } else if (code == LV_EVENT_RELEASED) {
                last_interaction_ms = millis();
                lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x2563EB), 0);
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "GIU DE NOI VOI AI");
                if (action_cb) action_cb("ai_ptt", "stop", 0);
            }
            return;
        }
        if (target == btn_intercom_ptt) {
            if (code == LV_EVENT_PRESSED) {
                last_interaction_ms = millis();
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0xDC2626), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "DANG PHAT AM...");
                if (action_cb) action_cb("intercom_ptt", "start", selected_room_idx);
            } else if (code == LV_EVENT_RELEASED) {
                last_interaction_ms = millis();
                lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x059669), 0);
                if (lbl_intercom_ptt) lv_label_set_text(lbl_intercom_ptt, "NHAN GIU DE NOI");
                if (action_cb) action_cb("intercom_ptt", "stop", selected_room_idx);
            }
            return;
        }

        // Click Events
        if (code != LV_EVENT_CLICKED) return;

        last_interaction_ms = millis();
        Serial.printf("[UI-EVENT] Clicked target %p\n", target);

        // Top Navigation buttons
        if (target == btn_toan_nha || cur_target == btn_toan_nha) {
            Serial.println("[UI] Clicked TOAN NHA -> Async switching to VIEW_MODE_ALL_ROOMS");
            request_view_mode(VIEW_MODE_ALL_ROOMS);
            return;
        }
        if (target == btn_nav_back_local || cur_target == btn_nav_back_local) {
            Serial.println("[UI] Clicked VE PHONG -> Async switching to VIEW_MODE_LOCAL");
            request_view_mode(VIEW_MODE_LOCAL);
            return;
        }
        if (target == btn_nav_back_rooms || cur_target == btn_nav_back_rooms) {
            Serial.println("[UI] Clicked DS PHONG -> Async switching to VIEW_MODE_ALL_ROOMS");
            request_view_mode(VIEW_MODE_ALL_ROOMS);
            return;
        }
        if (target == btn_master_off || cur_target == btn_master_off) {
            Serial.println("[UI] Clicked TAT HET TOAN NHA");
            if (action_cb) action_cb("master_turn_off_all", "", 0);
            return;
        }

        // Room Cards in ALL_ROOMS view
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            if (target == btn_room_cards[i] || cur_target == btn_room_cards[i]) {
                if (i < active_rooms_count) {
                    Serial.printf("[UI] Selected Room [%d]: %s\n", i, house_rooms[i].name);
                    request_view_mode(VIEW_MODE_REMOTE_ROOM, i);
                }
                return;
            }
        }

        // Local Device buttons
        for (int i = 0; i < local_buttons_count; i++) {
            if (target == local_buttons[i].btn_obj || cur_target == local_buttons[i].btn_obj) {
                bool is_climate = (local_buttons[i].icon == "climate" || local_buttons[i].entity_id.startsWith("climate"));
                if (is_climate) {
                    open_climate_dialog(&local_buttons[i]);
                } else if (local_buttons[i].entity_id.length() > 0 && action_cb) {
                    local_buttons[i].is_on = !local_buttons[i].is_on;
                    update_slot_ui(local_buttons[i]);
                    action_cb("entity_toggle", local_buttons[i].entity_id.c_str(), local_buttons[i].is_on);
                }
                return;
            }
        }

        // Remote Device buttons
        for (int i = 0; i < remote_buttons_count; i++) {
            if (target == remote_buttons[i].btn_obj || cur_target == remote_buttons[i].btn_obj) {
                bool is_climate = (remote_buttons[i].icon == "climate" || remote_buttons[i].entity_id.startsWith("climate"));
                if (is_climate) {
                    open_climate_dialog(&remote_buttons[i]);
                } else if (remote_buttons[i].entity_id.length() > 0 && action_cb) {
                    remote_buttons[i].is_on = !remote_buttons[i].is_on;
                    update_slot_ui(remote_buttons[i]);
                    if (selected_remote_room_idx >= 0 && selected_remote_room_idx < active_rooms_count) {
                        for (int d = 0; d < house_rooms[selected_remote_room_idx].device_count; d++) {
                            if (strcmp(house_rooms[selected_remote_room_idx].devices[d].entity_id, remote_buttons[i].entity_id.c_str()) == 0) {
                                house_rooms[selected_remote_room_idx].devices[d].is_on = remote_buttons[i].is_on;
                                break;
                            }
                        }
                    }
                    action_cb("entity_toggle", remote_buttons[i].entity_id.c_str(), remote_buttons[i].is_on);
                }
                return;
            }
        }

        // Climate Dialog Events
        if (target == btn_clim_close) {
            close_climate_dialog();
            return;
        }
        if (target == btn_clim_minus) {
            if (active_climate_slot) {
                active_climate_slot->temperature -= 0.5f;
                if (active_climate_slot->temperature < 16.0f) active_climate_slot->temperature = 16.0f;
                update_climate_dialog_ui();
                update_slot_ui(*active_climate_slot);
                pending_climate_flush = true;
                pending_climate_flush_ms = millis();
                pending_climate_target_temp = active_climate_slot->temperature;
            }
            return;
        }
        if (target == btn_clim_plus) {
            if (active_climate_slot) {
                active_climate_slot->temperature += 0.5f;
                if (active_climate_slot->temperature > 32.0f) active_climate_slot->temperature = 32.0f;
                update_climate_dialog_ui();
                update_slot_ui(*active_climate_slot);
                pending_climate_flush = true;
                pending_climate_flush_ms = millis();
                pending_climate_target_temp = active_climate_slot->temperature;
            }
            return;
        }
        if (target == btn_clim_eco26) {
            if (active_climate_slot) {
                active_climate_slot->temperature = 26.0f;
                active_climate_slot->hvac_mode = "cool";
                active_climate_slot->is_on = true;
                update_climate_dialog_ui();
                update_slot_ui(*active_climate_slot);
                if (action_cb) action_cb("climate_eco26", active_climate_slot->entity_id.c_str(), 26);
            }
            return;
        }
        const char* modes[] = {"cool", "fan_only", "dry", "auto"};
        for (int i = 0; i < 4; i++) {
            if (target == btn_clim_modes[i]) {
                if (active_climate_slot) {
                    const char* m = modes[i];
                    active_climate_slot->hvac_mode = m;
                    active_climate_slot->is_on = true;
                    update_climate_dialog_ui();
                    update_slot_ui(*active_climate_slot);
                    if (action_cb) action_cb("climate_mode", active_climate_slot->entity_id.c_str(), m[0]);
                }
                return;
            }
        }
        if (target == btn_clim_power) {
            if (active_climate_slot) {
                active_climate_slot->is_on = !active_climate_slot->is_on;
                active_climate_slot->hvac_mode = active_climate_slot->is_on ? "cool" : "off";
                update_climate_dialog_ui();
                update_slot_ui(*active_climate_slot);
                if (action_cb) action_cb("entity_toggle", active_climate_slot->entity_id.c_str(), active_climate_slot->is_on);
            }
            return;
        }
        if (target == btn_clim_fan) {
            if (active_climate_slot) {
                int cur_idx = 0;
                if (active_climate_slot->fan_mode == "low") cur_idx = 1;
                else if (active_climate_slot->fan_mode == "medium") cur_idx = 2;
                else if (active_climate_slot->fan_mode == "high") cur_idx = 3;
                int next_idx = (cur_idx + 1) % 4;
                const char* fan_modes[] = {"auto", "low", "medium", "high"};
                active_climate_slot->fan_mode = fan_modes[next_idx];
                update_climate_dialog_ui();
                if (action_cb) action_cb("climate_fan", active_climate_slot->entity_id.c_str(), next_idx);
            }
            return;
        }
        if (target == btn_clim_swing) {
            if (active_climate_slot) {
                active_climate_slot->swing_on = !active_climate_slot->swing_on;
                update_climate_dialog_ui();
                if (action_cb) action_cb("climate_swing", active_climate_slot->entity_id.c_str(), active_climate_slot->swing_on ? 1 : 0);
            }
            return;
        }

        // Intercom events
        if (target == btn_broadcast) {
            highlight_selected_room(-1);
            if (action_cb) action_cb("intercom_select", "broadcast", 0xFF);
            return;
        }
        for (int i = 0; i < 4; i++) {
            if (target == btn_rooms[i]) {
                highlight_selected_room(i);
                if (action_cb) action_cb("intercom_select", "room", intercom_targets[i].id);
                return;
            }
        }

        // Settings events
        if (target == btn_enter_ap) {
            if (action_cb) action_cb("settings_btn", "enter_ap", 0);
            return;
        }
        if (target == btn_test_speaker) {
            if (action_cb) action_cb("settings_btn", "test_speaker", 0);
            return;
        }
        if (target == btn_test_mic) {
            if (action_cb) action_cb("settings_btn", "test_mic", 0);
            return;
        }
        if (target == btn_test_ws) {
            if (action_cb) action_cb("settings_btn", "test_ws", 0);
            return;
        }
        if (target == btn_check_ota) {
            if (action_cb) action_cb("settings_btn", "check_ota", 0);
            return;
        }
        if (target == btn_toggle_ring) {
            ring_on_call_enabled = !ring_on_call_enabled;
            if (ring_on_call_enabled) {
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x0284C7), 0);
                lv_label_set_text(lbl_toggle_ring, "CHUONG: BAT");
            } else {
                lv_obj_set_style_bg_color(btn_toggle_ring, lv_color_hex(0x334155), 0);
                lv_label_set_text(lbl_toggle_ring, "CHUONG: TAT");
            }
            if (action_cb) action_cb("settings_btn", "toggle_ring", ring_on_call_enabled ? 1 : 0);
            return;
        }
    }

    void highlight_selected_room(int idx) {
        if (btn_broadcast) {
            if (idx == -1) {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x10B981), 0);
                lv_obj_set_style_border_color(btn_broadcast, lv_color_hex(0x34D399), 0);
                lv_obj_set_style_border_width(btn_broadcast, 2, 0);
            } else {
                lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x2563EB), 0);
                lv_obj_set_style_border_width(btn_broadcast, 0, 0);
            }
        }
        for (int i = 0; i < 4; i++) {
            if (!btn_rooms[i]) continue;
            if (i == idx) {
                lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x10B981), 0);
                lv_obj_set_style_border_color(btn_rooms[i], lv_color_hex(0x34D399), 0);
                lv_obj_set_style_border_width(btn_rooms[i], 2, 0);
            } else {
                lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x1F2937), 0);
                lv_obj_set_style_border_width(btn_rooms[i], 0, 0);
            }
        }
        selected_room_idx = (idx == -1) ? 0xFF : ((idx >= 0 && idx < active_intercom_targets_count) ? intercom_targets[idx].id : 0xFF);
    }

    void build_tab_devices() {
        lv_obj_clear_flag(tab_devices, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_clear_flag(tab_devices, LV_OBJ_FLAG_CLICKABLE);
        lv_obj_set_style_bg_color(tab_devices, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_devices, 0, 0);

        // 1. Top Navigation Bar (y = 2, h = 32)
        cont_top_nav = lv_obj_create(tab_devices);
        lv_obj_set_size(cont_top_nav, 236, 32);
        lv_obj_set_pos(cont_top_nav, 2, 2);
        lv_obj_set_style_bg_opa(cont_top_nav, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(cont_top_nav, 0, 0);
        lv_obj_set_style_pad_all(cont_top_nav, 0, 0);
        lv_obj_clear_flag(cont_top_nav, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_clear_flag(cont_top_nav, LV_OBJ_FLAG_CLICKABLE);

        // Button TOAN NHA (Left side)
        btn_toan_nha = lv_btn_create(cont_top_nav);
        lv_obj_set_size(btn_toan_nha, 120, 28);
        lv_obj_align(btn_toan_nha, LV_ALIGN_LEFT_MID, 0, 0);
        lv_obj_set_style_radius(btn_toan_nha, 8, 0);
        lv_obj_set_style_bg_color(btn_toan_nha, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_toan_nha, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_toan_nha, 1, 0);
        lv_obj_set_style_pad_all(btn_toan_nha, 0, 0);
        lv_obj_add_event_cb(btn_toan_nha, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_toan_nha = lv_label_create(btn_toan_nha);
        lv_obj_clear_flag(lbl_toan_nha, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_toan_nha, "TOAN NHA");
        lv_obj_set_style_text_font(lbl_toan_nha, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_toan_nha, lv_color_hex(0x38BDF8), 0);
        lv_obj_center(lbl_toan_nha);

        // Button TAT HET (Right side of local view)
        btn_master_off = lv_btn_create(cont_top_nav);
        lv_obj_set_size(btn_master_off, 80, 28);
        lv_obj_align(btn_master_off, LV_ALIGN_RIGHT_MID, 0, 0);
        lv_obj_set_style_radius(btn_master_off, 8, 0);
        lv_obj_set_style_bg_color(btn_master_off, lv_color_hex(0xDC2626), 0);
        lv_obj_set_style_pad_all(btn_master_off, 0, 0);
        lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_event_cb(btn_master_off, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_master_off = lv_label_create(btn_master_off);
        lv_obj_clear_flag(lbl_master_off, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_master_off, "TAT HET");
        lv_obj_set_style_text_font(lbl_master_off, &font_vietnamese_14, 0);
        lv_obj_center(lbl_master_off);

        // Title Label (For ALL_ROOMS or REMOTE_ROOM view)
        lbl_nav_title = lv_label_create(cont_top_nav);
        lv_obj_clear_flag(lbl_nav_title, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_nav_title, "CAC PHONG");
        lv_obj_set_style_text_font(lbl_nav_title, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_nav_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_align(lbl_nav_title, LV_ALIGN_LEFT_MID, 2, 0);
        lv_obj_add_flag(lbl_nav_title, LV_OBJ_FLAG_HIDDEN);

        // Back button to room list (DS PHONG)
        btn_nav_back_rooms = lv_btn_create(cont_top_nav);
        lv_obj_set_size(btn_nav_back_rooms, 74, 26);
        lv_obj_align(btn_nav_back_rooms, LV_ALIGN_RIGHT_MID, -80, 0);
        lv_obj_set_style_radius(btn_nav_back_rooms, 6, 0);
        lv_obj_set_style_bg_color(btn_nav_back_rooms, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_nav_back_rooms, lv_color_hex(0x475569), 0);
        lv_obj_set_style_border_width(btn_nav_back_rooms, 1, 0);
        lv_obj_set_style_pad_all(btn_nav_back_rooms, 0, 0);
        lv_obj_add_flag(btn_nav_back_rooms, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_event_cb(btn_nav_back_rooms, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_nav_back_rooms = lv_label_create(btn_nav_back_rooms);
        lv_obj_clear_flag(lbl_nav_back_rooms, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_nav_back_rooms, "DS PHONG");
        lv_obj_set_style_text_font(lbl_nav_back_rooms, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_nav_back_rooms, lv_color_hex(0x94A3B8), 0);
        lv_obj_center(lbl_nav_back_rooms);

        // Back button to local room (VE PHONG)
        btn_nav_back_local = lv_btn_create(cont_top_nav);
        lv_obj_set_size(btn_nav_back_local, 76, 26);
        lv_obj_align(btn_nav_back_local, LV_ALIGN_RIGHT_MID, 0, 0);
        lv_obj_set_style_radius(btn_nav_back_local, 6, 0);
        lv_obj_set_style_bg_color(btn_nav_back_local, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_pad_all(btn_nav_back_local, 0, 0);
        lv_obj_add_flag(btn_nav_back_local, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_event_cb(btn_nav_back_local, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_nav_back_local = lv_label_create(btn_nav_back_local);
        lv_obj_clear_flag(lbl_nav_back_local, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_nav_back_local, "VE PHONG");
        lv_obj_set_style_text_font(lbl_nav_back_local, &font_vietnamese_14, 0);
        lv_obj_center(lbl_nav_back_local);

        // 2. Content Area (y = 36, h = 206) - NO scroll interception unless > 8 items
        cont_devices_scroll = lv_obj_create(tab_devices);
        lv_obj_set_size(cont_devices_scroll, 236, 206);
        lv_obj_set_pos(cont_devices_scroll, 2, 36);
        lv_obj_set_style_bg_opa(cont_devices_scroll, LV_OPA_TRANSP, 0);
        lv_obj_set_style_border_width(cont_devices_scroll, 0, 0);
        lv_obj_set_style_pad_all(cont_devices_scroll, 0, 0);
        lv_obj_clear_flag(cont_devices_scroll, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_clear_flag(cont_devices_scroll, LV_OBJ_FLAG_CLICKABLE);

        // 3. Room Cards inside Container
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            btn_room_cards[i] = lv_btn_create(cont_devices_scroll);
            lv_obj_set_size(btn_room_cards[i], 114, 46);
            int x = (i % 2 == 0) ? 2 : 120;
            int y = (i / 2) * 50;
            lv_obj_set_pos(btn_room_cards[i], x, y);
            lv_obj_set_style_radius(btn_room_cards[i], 8, 0);
            lv_obj_set_style_bg_color(btn_room_cards[i], lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(btn_room_cards[i], lv_color_hex(0x334155), 0);
            lv_obj_set_style_border_width(btn_room_cards[i], 1, 0);
            lv_obj_set_style_pad_all(btn_room_cards[i], 2, 0);
            lv_obj_add_flag(btn_room_cards[i], LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_event_cb(btn_room_cards[i], event_handler_trampoline, LV_EVENT_CLICKED, this);

            lbl_room_cards[i] = lv_label_create(btn_room_cards[i]);
            lv_obj_clear_flag(lbl_room_cards[i], LV_OBJ_FLAG_CLICKABLE);
            lv_obj_set_style_text_font(lbl_room_cards[i], &font_vietnamese_14, 0);
            lv_obj_set_style_text_color(lbl_room_cards[i], lv_color_hex(0xF8FAFC), 0);
            lv_obj_center(lbl_room_cards[i]);
        }

        // 4. Local Device Buttons inside Container
        for (int i = 0; i < MAX_LOCAL_BUTTONS; i++) {
            local_buttons[i].btn_obj = lv_btn_create(cont_devices_scroll);
            lv_obj_set_size(local_buttons[i].btn_obj, 114, 46);
            int x = (i % 2 == 0) ? 2 : 120;
            int y = (i / 2) * 50;
            lv_obj_set_pos(local_buttons[i].btn_obj, x, y);
            lv_obj_set_style_radius(local_buttons[i].btn_obj, 8, 0);
            lv_obj_set_style_bg_color(local_buttons[i].btn_obj, lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(local_buttons[i].btn_obj, lv_color_hex(0x475569), 0);
            lv_obj_set_style_border_width(local_buttons[i].btn_obj, 1, 0);
            lv_obj_set_style_pad_all(local_buttons[i].btn_obj, 2, 0);
            lv_obj_add_flag(local_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_event_cb(local_buttons[i].btn_obj, event_handler_trampoline, LV_EVENT_CLICKED, this);

            local_buttons[i].lbl_obj = lv_label_create(local_buttons[i].btn_obj);
            lv_obj_clear_flag(local_buttons[i].lbl_obj, LV_OBJ_FLAG_CLICKABLE);
            lv_obj_set_style_text_font(local_buttons[i].lbl_obj, &font_vietnamese_14, 0);
            lv_obj_set_style_text_color(local_buttons[i].lbl_obj, lv_color_hex(0xF8FAFC), 0);
            lv_obj_center(local_buttons[i].lbl_obj);
        }

        // 5. Remote Device Buttons inside Container
        for (int i = 0; i < MAX_REMOTE_BUTTONS; i++) {
            remote_buttons[i].btn_obj = lv_btn_create(cont_devices_scroll);
            lv_obj_set_size(remote_buttons[i].btn_obj, 114, 46);
            int x = (i % 2 == 0) ? 2 : 120;
            int y = (i / 2) * 50;
            lv_obj_set_pos(remote_buttons[i].btn_obj, x, y);
            lv_obj_set_style_radius(remote_buttons[i].btn_obj, 8, 0);
            lv_obj_set_style_bg_color(remote_buttons[i].btn_obj, lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(remote_buttons[i].btn_obj, lv_color_hex(0x475569), 0);
            lv_obj_set_style_border_width(remote_buttons[i].btn_obj, 1, 0);
            lv_obj_set_style_pad_all(remote_buttons[i].btn_obj, 2, 0);
            lv_obj_add_flag(remote_buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_event_cb(remote_buttons[i].btn_obj, event_handler_trampoline, LV_EVENT_CLICKED, this);

            remote_buttons[i].lbl_obj = lv_label_create(remote_buttons[i].btn_obj);
            lv_obj_clear_flag(remote_buttons[i].lbl_obj, LV_OBJ_FLAG_CLICKABLE);
            lv_obj_set_style_text_font(remote_buttons[i].lbl_obj, &font_vietnamese_14, 0);
            lv_obj_set_style_text_color(remote_buttons[i].lbl_obj, lv_color_hex(0xF8FAFC), 0);
            lv_obj_center(remote_buttons[i].lbl_obj);
        }
    }

    void build_tab_ai() {
        lv_obj_clear_flag(tab_ai, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_ai, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_ai, 6, 0);

        lbl_ai_state = lv_label_create(tab_ai);
        lv_label_set_text(lbl_ai_state, "AI: San sang (Cho lenh)");
        lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_ai_state, &font_vietnamese_14, 0);
        lv_obj_align(lbl_ai_state, LV_ALIGN_TOP_MID, 0, 4);

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

        ta_ai_response = lv_textarea_create(tab_ai);
        lv_obj_set_size(ta_ai_response, 228, 86);
        lv_obj_align(ta_ai_response, LV_ALIGN_TOP_MID, 0, 74);
        lv_obj_set_style_bg_color(ta_ai_response, lv_color_hex(0x0F172A), 0);
        lv_obj_set_style_text_color(ta_ai_response, lv_color_hex(0xE2E8F0), 0);
        lv_obj_set_style_border_color(ta_ai_response, lv_color_hex(0x334155), 0);
        lv_obj_set_style_radius(ta_ai_response, 10, 0);
        lv_obj_set_style_text_font(ta_ai_response, &font_vietnamese_14, 0);
        lv_textarea_set_text(ta_ai_response, "Xin chao! Nhan giu nut ben duoi de noi chuyen voi Nala AI...");

        btn_ai_ptt = lv_btn_create(tab_ai);
        lv_obj_set_size(btn_ai_ptt, 228, 48);
        lv_obj_align(btn_ai_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_ai_ptt, lv_color_hex(0x2563EB), 0);
        lv_obj_set_style_radius(btn_ai_ptt, 12, 0);
        lv_obj_add_event_cb(btn_ai_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_ai_ptt_text = lv_label_create(btn_ai_ptt);
        lv_label_set_text(lbl_ai_ptt_text, "GIU DE NOI VOI AI");
        lv_obj_set_style_text_font(lbl_ai_ptt_text, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ai_ptt_text);
    }

    void build_tab_intercom() {
        lv_obj_clear_flag(tab_intercom, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_intercom, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_intercom, 6, 0);

        lbl_intercom_status = lv_label_create(tab_intercom);
        lv_label_set_text(lbl_intercom_status, "Dam thoai: San sang");
        lv_obj_set_style_text_color(lbl_intercom_status, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_intercom_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_intercom_status, LV_ALIGN_TOP_MID, 0, 2);

        btn_broadcast = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_broadcast, 228, 36);
        lv_obj_align(btn_broadcast, LV_ALIGN_TOP_MID, 0, 24);
        lv_obj_set_style_bg_color(btn_broadcast, lv_color_hex(0x2563EB), 0);
        lv_obj_set_style_radius(btn_broadcast, 8, 0);
        lv_obj_add_event_cb(btn_broadcast, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lv_obj_t* lbl_all = lv_label_create(btn_broadcast);
        lv_label_set_text(lbl_all, "GOI TOAN NHA (ALL)");
        lv_obj_set_style_text_font(lbl_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_all);

        for (int i = 0; i < 4; i++) {
            btn_rooms[i] = lv_btn_create(tab_intercom);
            lv_obj_set_size(btn_rooms[i], 110, 36);
            int x = (i % 2 == 0) ? 2 : 118;
            int y = 66 + (i / 2) * 42;
            lv_obj_set_pos(btn_rooms[i], x, y);
            lv_obj_set_style_bg_color(btn_rooms[i], lv_color_hex(0x1F2937), 0);
            lv_obj_set_style_radius(btn_rooms[i], 8, 0);
            lv_obj_add_event_cb(btn_rooms[i], event_handler_trampoline, LV_EVENT_CLICKED, this);
            lv_obj_add_flag(btn_rooms[i], LV_OBJ_FLAG_HIDDEN);

            lbl_rooms[i] = lv_label_create(btn_rooms[i]);
            lv_label_set_text(lbl_rooms[i], "Phong");
            lv_obj_set_style_text_font(lbl_rooms[i], &font_vietnamese_14, 0);
            lv_obj_center(lbl_rooms[i]);
        }

        btn_intercom_ptt = lv_btn_create(tab_intercom);
        lv_obj_set_size(btn_intercom_ptt, 228, 48);
        lv_obj_align(btn_intercom_ptt, LV_ALIGN_BOTTOM_MID, 0, -4);
        lv_obj_set_style_bg_color(btn_intercom_ptt, lv_color_hex(0x059669), 0);
        lv_obj_set_style_radius(btn_intercom_ptt, 12, 0);
        lv_obj_add_event_cb(btn_intercom_ptt, event_handler_trampoline, LV_EVENT_ALL, this);

        lbl_intercom_ptt = lv_label_create(btn_intercom_ptt);
        lv_label_set_text(lbl_intercom_ptt, "NHAN GIU DE NOI");
        lv_obj_set_style_text_font(lbl_intercom_ptt, &font_vietnamese_14, 0);
        lv_obj_center(lbl_intercom_ptt);
    }

    void build_tab_settings(uint8_t init_vol, uint8_t init_bright, uint8_t init_mic_gain) {
        lv_obj_clear_flag(tab_settings, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_set_style_bg_color(tab_settings, lv_color_hex(0x080C14), 0);
        lv_obj_set_style_pad_all(tab_settings, 6, 0);

        // 1. Slider Am Luong
        lv_obj_t* lbl_vol = lv_label_create(tab_settings);
        lv_label_set_text(lbl_vol, "Am Luong Loa:");
        lv_obj_set_style_text_font(lbl_vol, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_vol, 4, 2);

        slider_vol = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_vol, 160, 10);
        lv_obj_set_pos(slider_vol, 4, 20);
        lv_slider_set_range(slider_vol, 0, 100);
        lv_slider_set_value(slider_vol, init_vol, LV_ANIM_OFF);
        lv_obj_add_event_cb(slider_vol, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        lbl_vol_val = lv_label_create(tab_settings);
        char vbuf[16];
        snprintf(vbuf, sizeof(vbuf), "%d%%", init_vol);
        lv_label_set_text(lbl_vol_val, vbuf);
        lv_obj_set_style_text_font(lbl_vol_val, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_vol_val, 174, 16);

        // 2. Slider Do Sang
        lv_obj_t* lbl_bright = lv_label_create(tab_settings);
        lv_label_set_text(lbl_bright, "Do Sang Man Hinh:");
        lv_obj_set_style_text_font(lbl_bright, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_bright, 4, 36);

        slider_bright = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_bright, 160, 10);
        lv_obj_set_pos(slider_bright, 4, 54);
        lv_slider_set_range(slider_bright, 20, 255);
        lv_slider_set_value(slider_bright, init_bright, LV_ANIM_OFF);
        lv_obj_add_event_cb(slider_bright, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        lbl_bright_val = lv_label_create(tab_settings);
        char bbuf[16];
        snprintf(bbuf, sizeof(bbuf), "%d%%", (init_bright * 100) / 255);
        lv_label_set_text(lbl_bright_val, bbuf);
        lv_obj_set_style_text_font(lbl_bright_val, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_bright_val, 174, 50);

        // 3. Slider Do Nhay Mic
        lv_obj_t* lbl_m = lv_label_create(tab_settings);
        lv_label_set_text(lbl_m, "Do Nhay Mic Thu Am:");
        lv_obj_set_style_text_font(lbl_m, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_m, 4, 70);

        slider_mic = lv_slider_create(tab_settings);
        lv_obj_set_size(slider_mic, 120, 10);
        lv_obj_set_pos(slider_mic, 4, 88);
        lv_slider_set_range(slider_mic, 1, 7);
        lv_slider_set_value(slider_mic, init_mic_gain, LV_ANIM_OFF);
        lv_obj_add_event_cb(slider_mic, event_handler_trampoline, LV_EVENT_VALUE_CHANGED, this);

        lbl_mic_val = lv_label_create(tab_settings);
        const char* gain_names[8] = {"", "Thap", "Vua", "Chuan", "Nhay", "Rat nhay", "Cuc nhay", "Toi da"};
        char mbuf[32];
        snprintf(mbuf, sizeof(mbuf), "Muc %d (%s)", init_mic_gain, (init_mic_gain >= 1 && init_mic_gain <= 7) ? gain_names[init_mic_gain] : "");
        lv_label_set_text(lbl_mic_val, mbuf);
        lv_obj_set_style_text_font(lbl_mic_val, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_mic_val, 132, 84);

        // 4. Test Buttons Row 1 (y = 106)
        btn_test_speaker = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_speaker, 108, 30);
        lv_obj_set_pos(btn_test_speaker, 4, 106);
        lv_obj_set_style_bg_color(btn_test_speaker, lv_color_hex(0x1E3A8A), 0);
        lv_obj_set_style_radius(btn_test_speaker, 6, 0);
        lv_obj_add_event_cb(btn_test_speaker, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ts = lv_label_create(btn_test_speaker);
        lv_label_set_text(lbl_ts, "TEST LOA");
        lv_obj_set_style_text_font(lbl_ts, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ts);

        btn_test_mic = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_mic, 108, 30);
        lv_obj_set_pos(btn_test_mic, 120, 106);
        lv_obj_set_style_bg_color(btn_test_mic, lv_color_hex(0x065F46), 0);
        lv_obj_set_style_radius(btn_test_mic, 6, 0);
        lv_obj_add_event_cb(btn_test_mic, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tm = lv_label_create(btn_test_mic);
        lv_label_set_text(lbl_tm, "TEST MIC");
        lv_obj_set_style_text_font(lbl_tm, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tm);

        // 5. Test Buttons Row 2 (y = 142)
        btn_test_ws = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_test_ws, 108, 30);
        lv_obj_set_pos(btn_test_ws, 4, 142);
        lv_obj_set_style_bg_color(btn_test_ws, lv_color_hex(0x581C87), 0);
        lv_obj_set_style_radius(btn_test_ws, 6, 0);
        lv_obj_add_event_cb(btn_test_ws, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_tw = lv_label_create(btn_test_ws);
        lv_label_set_text(lbl_tw, "TEST SERVER");
        lv_obj_set_style_text_font(lbl_tw, &font_vietnamese_14, 0);
        lv_obj_center(lbl_tw);

        btn_enter_ap = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_enter_ap, 108, 30);
        lv_obj_set_pos(btn_enter_ap, 120, 142);
        lv_obj_set_style_bg_color(btn_enter_ap, lv_color_hex(0x92400E), 0);
        lv_obj_set_style_radius(btn_enter_ap, 6, 0);
        lv_obj_add_event_cb(btn_enter_ap, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ap = lv_label_create(btn_enter_ap);
        lv_label_set_text(lbl_ap, "DOI WIFI");
        lv_obj_set_style_text_font(lbl_ap, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ap);

        // 6. Test Buttons Row 3 (y = 178)
        btn_check_ota = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_check_ota, 108, 30);
        lv_obj_set_pos(btn_check_ota, 4, 178);
        lv_obj_set_style_bg_color(btn_check_ota, lv_color_hex(0x0284C7), 0);
        lv_obj_set_style_radius(btn_check_ota, 6, 0);
        lv_obj_add_event_cb(btn_check_ota, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_ota = lv_label_create(btn_check_ota);
        lv_label_set_text(lbl_ota, "KIEM TRA OTA");
        lv_obj_set_style_text_font(lbl_ota, &font_vietnamese_14, 0);
        lv_obj_center(lbl_ota);

        btn_toggle_ring = lv_btn_create(tab_settings);
        lv_obj_set_size(btn_toggle_ring, 108, 30);
        lv_obj_set_pos(btn_toggle_ring, 120, 178);
        lv_obj_set_style_bg_color(btn_toggle_ring, ring_on_call_enabled ? lv_color_hex(0x0284C7) : lv_color_hex(0x334155), 0);
        lv_obj_set_style_radius(btn_toggle_ring, 6, 0);
        lv_obj_add_event_cb(btn_toggle_ring, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_toggle_ring = lv_label_create(btn_toggle_ring);
        lv_obj_clear_flag(lbl_toggle_ring, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_toggle_ring, ring_on_call_enabled ? "CHUONG: BAT" : "CHUONG: TAT");
        lv_obj_set_style_text_font(lbl_toggle_ring, &font_vietnamese_14, 0);
        lv_obj_center(lbl_toggle_ring);

        // 7. Thong tin Firmware
        lbl_firmware_ver = lv_label_create(tab_settings);
        lv_label_set_text(lbl_firmware_ver, "Ban: v3.0.3 | PSRAM: 0.0MB");
        lv_obj_set_style_text_color(lbl_firmware_ver, lv_color_hex(0x34D399), 0);
        lv_obj_set_style_text_font(lbl_firmware_ver, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_firmware_ver, 4, 212);

        lbl_net_info = lv_label_create(tab_settings);
        lv_label_set_text(lbl_net_info, "Cham giu Header 2s de doi WiFi.");
        lv_obj_set_style_text_color(lbl_net_info, lv_color_hex(0x64748B), 0);
        lv_obj_set_style_text_font(lbl_net_info, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_net_info, 4, 226);
    }

    void build_incoming_call_modal(lv_obj_t* parent) {
        modal_incoming_call = lv_obj_create(parent);
        lv_obj_set_size(modal_incoming_call, 230, 130);
        lv_obj_align(modal_incoming_call, LV_ALIGN_CENTER, 0, -10);
        lv_obj_set_style_bg_color(modal_incoming_call, lv_color_hex(0x0B1326), 0);
        lv_obj_set_style_border_color(modal_incoming_call, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(modal_incoming_call, 2, 0);
        lv_obj_set_style_radius(modal_incoming_call, 14, 0);
        lv_obj_clear_flag(modal_incoming_call, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_flag(modal_incoming_call, LV_OBJ_FLAG_HIDDEN);

        lbl_incoming_title = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_title, "CUOC GOI NOI BO");
        lv_obj_set_style_text_color(lbl_incoming_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_incoming_title, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_title, LV_ALIGN_TOP_MID, 0, 4);

        lbl_incoming_caller = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_caller, "Dang ket noi...");
        lv_obj_set_style_text_color(lbl_incoming_caller, lv_color_hex(0xFFFFFF), 0);
        lv_obj_set_style_text_font(lbl_incoming_caller, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_caller, LV_ALIGN_CENTER, 0, -4);

        lbl_incoming_status = lv_label_create(modal_incoming_call);
        lv_label_set_text(lbl_incoming_status, "Dang dam thoai truc tiep...");
        lv_obj_set_style_text_color(lbl_incoming_status, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_incoming_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_incoming_status, LV_ALIGN_BOTTOM_MID, 0, -6);
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

        // Header: Tieu de + Nut Dong [X]
        lbl_clim_title = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_title, "DIEU KHIEN MAY LANH");
        lv_obj_set_style_text_color(lbl_clim_title, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_text_font(lbl_clim_title, &font_vietnamese_14, 0);
        lv_obj_set_pos(lbl_clim_title, 6, 4);

        btn_clim_close = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_close, 26, 26);
        lv_obj_set_pos(btn_clim_close, 194, 2);
        lv_obj_set_style_radius(btn_clim_close, 13, 0);
        lv_obj_set_style_bg_color(btn_clim_close, lv_color_hex(0x334155), 0);
        lv_obj_add_event_cb(btn_clim_close, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_cx = lv_label_create(btn_clim_close);
        lv_label_set_text(lbl_cx, "X");
        lv_obj_set_style_text_font(lbl_cx, &font_vietnamese_14, 0);
        lv_obj_center(lbl_cx);

        // Temp Controls
        btn_clim_minus = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_minus, 46, 38);
        lv_obj_set_pos(btn_clim_minus, 4, 34);
        lv_obj_set_style_bg_color(btn_clim_minus, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_minus, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_clim_minus, 1, 0);
        lv_obj_set_style_radius(btn_clim_minus, 8, 0);
        lv_obj_add_event_cb(btn_clim_minus, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_m = lv_label_create(btn_clim_minus);
        lv_label_set_text(lbl_m, "-");
        lv_obj_set_style_text_font(lbl_m, &font_vietnamese_16, 0);
        lv_obj_center(lbl_m);

        lbl_clim_temp = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_temp, "26.0*C");
        lv_obj_set_style_text_font(lbl_clim_temp, &font_vietnamese_16, 0);
        lv_obj_set_style_text_color(lbl_clim_temp, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_pos(lbl_clim_temp, 76, 42);

        btn_clim_plus = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_plus, 46, 38);
        lv_obj_set_pos(btn_clim_plus, 174, 34);
        lv_obj_set_style_bg_color(btn_clim_plus, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_plus, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(btn_clim_plus, 1, 0);
        lv_obj_set_style_radius(btn_clim_plus, 8, 0);
        lv_obj_add_event_cb(btn_clim_plus, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_p = lv_label_create(btn_clim_plus);
        lv_label_set_text(lbl_p, "+");
        lv_obj_set_style_text_font(lbl_p, &font_vietnamese_16, 0);
        lv_obj_center(lbl_p);

        // Status Strip
        lbl_clim_status = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_status, "Phong: 28.0*C - Lam Mat");
        lv_obj_set_style_text_color(lbl_clim_status, lv_color_hex(0x10B981), 0);
        lv_obj_set_style_text_font(lbl_clim_status, &font_vietnamese_14, 0);
        lv_obj_align(lbl_clim_status, LV_ALIGN_TOP_MID, 0, 78);

        // Mode Row (4 nut)
        const char* m_labels[] = {"Mat", "Gio", "Kho", "Auto"};
        for (int i = 0; i < 4; i++) {
            btn_clim_modes[i] = lv_btn_create(dialog_climate);
            lv_obj_set_size(btn_clim_modes[i], 52, 28);
            lv_obj_set_pos(btn_clim_modes[i], 4 + i * 56, 98);
            lv_obj_set_style_bg_color(btn_clim_modes[i], lv_color_hex(0x1E293B), 0);
            lv_obj_set_style_border_color(btn_clim_modes[i], lv_color_hex(0x334155), 0);
            lv_obj_set_style_border_width(btn_clim_modes[i], 1, 0);
            lv_obj_set_style_radius(btn_clim_modes[i], 6, 0);
            lv_obj_add_event_cb(btn_clim_modes[i], event_handler_trampoline, LV_EVENT_CLICKED, this);
            lv_obj_t* l = lv_label_create(btn_clim_modes[i]);
            lv_label_set_text(l, m_labels[i]);
            lv_obj_set_style_text_font(l, &font_vietnamese_14, 0);
            lv_obj_center(l);
        }

        // Action Buttons Row (Nguon & Quat)
        btn_clim_power = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_power, 108, 34);
        lv_obj_set_pos(btn_clim_power, 4, 132);
        lv_obj_set_style_bg_color(btn_clim_power, lv_color_hex(0x059669), 0);
        lv_obj_set_style_radius(btn_clim_power, 8, 0);
        lv_obj_add_event_cb(btn_clim_power, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_clim_power = lv_label_create(btn_clim_power);
        lv_label_set_text(lbl_clim_power, "BAT NGUON");
        lv_obj_set_style_text_font(lbl_clim_power, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_power);

        btn_clim_fan = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_fan, 108, 34);
        lv_obj_set_pos(btn_clim_fan, 116, 132);
        lv_obj_set_style_bg_color(btn_clim_fan, lv_color_hex(0x1E293B), 0);
        lv_obj_set_style_border_color(btn_clim_fan, lv_color_hex(0x334155), 0);
        lv_obj_set_style_border_width(btn_clim_fan, 1, 0);
        lv_obj_set_style_radius(btn_clim_fan, 8, 0);
        lv_obj_add_event_cb(btn_clim_fan, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lbl_clim_fan = lv_label_create(btn_clim_fan);
        lv_label_set_text(lbl_clim_fan, "Quat: Tu Dong");
        lv_obj_set_style_text_font(lbl_clim_fan, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_fan);

        // ECO 26*C & Dao Gio
        btn_clim_eco26 = lv_btn_create(dialog_climate);
        lv_obj_set_size(btn_clim_eco26, 108, 32);
        lv_obj_set_pos(btn_clim_eco26, 4, 172);
        lv_obj_set_style_bg_color(btn_clim_eco26, lv_color_hex(0x065F46), 0);
        lv_obj_set_style_radius(btn_clim_eco26, 8, 0);
        lv_obj_add_event_cb(btn_clim_eco26, event_handler_trampoline, LV_EVENT_CLICKED, this);
        lv_obj_t* lbl_e26 = lv_label_create(btn_clim_eco26);
        lv_label_set_text(lbl_e26, "ECO 26*C");
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
        lv_label_set_text(lbl_clim_swing, "Dao Gio: TAT");
        lv_obj_set_style_text_font(lbl_clim_swing, &font_vietnamese_14, 0);
        lv_obj_center(lbl_clim_swing);

        // Strip Info
        lbl_clim_info = lv_label_create(dialog_climate);
        lv_label_set_text(lbl_clim_info, "Phong: 28.0*C | Cai dat: 26.0*C");
        lv_obj_set_style_text_color(lbl_clim_info, lv_color_hex(0x94A3B8), 0);
        lv_obj_set_style_text_font(lbl_clim_info, &font_vietnamese_14, 0);
        lv_obj_align(lbl_clim_info, LV_ALIGN_BOTTOM_MID, 0, -4);
    }

    void open_climate_dialog(UIButtonSlot* slot) {
        if (!slot) return;
        active_climate_slot = slot;
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
        active_climate_slot = nullptr;
    }

    void update_climate_dialog_ui() {
        if (!active_climate_slot) return;
        UIButtonSlot& b = *active_climate_slot;

        if (lbl_clim_title) {
            char title_buf[64];
            snprintf(title_buf, sizeof(title_buf), "%s", b.name.c_str());
            lv_label_set_text(lbl_clim_title, title_buf);
        }

        if (lbl_clim_temp) {
            char temp_buf[32];
            snprintf(temp_buf, sizeof(temp_buf), "%.1f*C", b.temperature > 10.0f ? b.temperature : 26.0f);
            lv_label_set_text(lbl_clim_temp, temp_buf);
        }

        if (lbl_clim_status) {
            float room_t = b.current_temperature > 10.0f ? b.current_temperature : 28.0f;
            const char* st_name = "Tat";
            uint32_t st_color = 0x94A3B8;
            if (b.is_on && b.hvac_mode != "off") {
                if (b.hvac_mode == "cool") {
                    st_name = "Dang Lam Mat";
                    st_color = 0x06B6D4;
                } else if (b.hvac_mode == "fan_only") {
                    st_name = "Quat Gio";
                    st_color = 0xA78BFA;
                } else if (b.hvac_mode == "dry") {
                    st_name = "Hut Am";
                    st_color = 0x10B981;
                } else if (b.hvac_mode == "auto") {
                    st_name = "Tu Dong";
                    st_color = 0xF59E0B;
                }
            }
            char st_buf[64];
            snprintf(st_buf, sizeof(st_buf), "Phong: %.1f*C - %s", room_t, st_name);
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
                lv_label_set_text(lbl_clim_power, "TAT NGUON");
            } else {
                lv_obj_set_style_bg_color(btn_clim_power, lv_color_hex(0x059669), 0);
                lv_label_set_text(lbl_clim_power, "BAT NGUON");
            }
        }

        if (lbl_clim_fan) {
            const char* fan_lbl = "Quat: Tu Dong";
            if (b.fan_mode == "low") fan_lbl = "Quat: Nhe";
            else if (b.fan_mode == "medium") fan_lbl = "Quat: Vua";
            else if (b.fan_mode == "high") fan_lbl = "Quat: Manh";
            lv_label_set_text(lbl_clim_fan, fan_lbl);
        }

        if (btn_clim_swing && lbl_clim_swing) {
            if (b.swing_on) {
                lv_obj_set_style_bg_color(btn_clim_swing, lv_color_hex(0x0284C7), 0);
                lv_label_set_text(lbl_clim_swing, "Dao Gio: BAT");
            } else {
                lv_obj_set_style_bg_color(btn_clim_swing, lv_color_hex(0x1E293B), 0);
                lv_label_set_text(lbl_clim_swing, "Dao Gio: TAT");
            }
        }

        if (lbl_clim_info) {
            float room_t = b.current_temperature > 10.0f ? b.current_temperature : 28.0f;
            float set_t = b.temperature > 10.0f ? b.temperature : 26.0f;
            char if_buf[64];
            snprintf(if_buf, sizeof(if_buf), "Phong: %.1f*C | Cai dat: %.1f*C", room_t, set_t);
            lv_label_set_text(lbl_clim_info, if_buf);
        }
    }
};
