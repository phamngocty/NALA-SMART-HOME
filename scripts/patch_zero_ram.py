import re

# -------------------------------------------------------------
# 1. PATCH UI_LVGL_DASHBOARD.H
# -------------------------------------------------------------
path_h = 'firmware_esp32s3_panel/include/ui_lvgl_dashboard.h'
with open(path_h, 'r', encoding='utf-8') as f:
    code_h = f.read()

old_h_top = """#define MAX_DASHBOARD_BUTTONS 16
#define MAX_ROOM_CHIPS 6

typedef void (*UIActionCallback_t)(const char* target, const char* action, int value);"""

new_h_top = """#define MAX_DASHBOARD_BUTTONS 16
#define MAX_ROOM_CHIPS 6
#define MAX_CACHED_ROOMS 8
#define MAX_ROOM_DEVICES 8

enum DashboardViewMode {
    VIEW_HOME_ROOM = 0,
    VIEW_ROOM_LIST = 1,
    VIEW_REMOTE_ROOM = 2
};

struct CompactDevice_t {
    char id[16];
    char name[20];
    char entity_id[48];
    char icon[12];
    bool is_on;
    float temperature;
    float current_temperature;
    char hvac_mode[12];
    char fan_mode[12];
    bool swing_on;
};

struct CachedRoom_t {
    char name[24];
    char floor[16];
    uint8_t active_count;
    uint8_t total_count;
    uint8_t devices_count;
    CompactDevice_t devices[MAX_ROOM_DEVICES];
};

typedef void (*UIActionCallback_t)(const char* target, const char* action, int value);"""

assert old_h_top in code_h, "old_h_top not found"
code_h = code_h.replace(old_h_top, new_h_top, 1)

old_h_members = """    // 2-Column Scrollable Grid
    lv_obj_t* cont_devices_scroll;"""

new_h_members = """    // 2-Column Scrollable Grid
    lv_obj_t* cont_devices_scroll;

    // Zero-RAM Smart Floor & Room Navigation State
    DashboardViewMode current_view_mode;
    char home_room_name[28];
    uint8_t room_view_timeout_sec;
    uint32_t last_remote_touch_ms;

    // Static backup for Home Room buttons (Zero Heap overhead)
    CompactDevice_t home_devices_backup[MAX_DASHBOARD_BUTTONS];
    uint8_t home_devices_count;

    // Static cache for all rooms and their devices (Zero Heap overhead)
    CachedRoom_t cached_rooms[MAX_CACHED_ROOMS];
    uint8_t cached_rooms_count;
    uint8_t active_remote_room_idx;

    // Return button widget in cont_room_chips
    lv_obj_t* btn_home_return;
    lv_obj_t* lbl_home_return;

    // Cached House Status
    char cached_house_summary[64];
    uint32_t cached_house_alert_color;
    bool cached_has_active_devices;"""

assert old_h_members in code_h, "old_h_members not found"
code_h = code_h.replace(old_h_members, new_h_members, 1)

old_ctor_init = """          strip_house_alert(nullptr), lbl_house_alert(nullptr), btn_master_off(nullptr), lbl_master_off(nullptr),
          cont_devices_scroll(nullptr),"""

new_ctor_init = """          strip_house_alert(nullptr), lbl_house_alert(nullptr), btn_master_off(nullptr), lbl_master_off(nullptr),
          cont_devices_scroll(nullptr),
          current_view_mode(VIEW_HOME_ROOM), room_view_timeout_sec(15), last_remote_touch_ms(0),
          home_devices_count(0), cached_rooms_count(0), active_remote_room_idx(0),
          btn_home_return(nullptr), lbl_home_return(nullptr),
          cached_house_alert_color(0x10B981), cached_has_active_devices(false),"""

assert old_ctor_init in code_h, "old_ctor_init not found"
code_h = code_h.replace(old_ctor_init, new_ctor_init, 1)

old_ctor_body = """        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            chip_rooms[i] = nullptr;
            lbl_chip_rooms[i] = nullptr;
            chip_room_names[i][0] = '\\0';
        }"""

new_ctor_body = """        strncpy(home_room_name, "Thiết Bị", sizeof(home_room_name));
        strncpy(cached_house_summary, "Tất cả thiết bị tắt", sizeof(cached_house_summary));
        for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
            chip_rooms[i] = nullptr;
            lbl_chip_rooms[i] = nullptr;
            chip_room_names[i][0] = '\\0';
        }"""

assert old_ctor_body in code_h, "old_ctor_body not found"
code_h = code_h.replace(old_ctor_body, new_ctor_body, 1)

old_init = """    void init(const char* room_name, const char* ip_str, const char* pair_code, 
              uint8_t init_vol, uint8_t init_bright, bool init_ring_on_call = true, uint8_t init_mic_gain = 5) {
        ring_on_call_enabled = init_ring_on_call;"""

new_init = """    void init(const char* room_name, const char* ip_str, const char* pair_code, 
              uint8_t init_vol, uint8_t init_bright, bool init_ring_on_call = true, uint8_t init_mic_gain = 5) {
        ring_on_call_enabled = init_ring_on_call;
        current_view_mode = VIEW_HOME_ROOM;
        room_view_timeout_sec = 15;
        last_remote_touch_ms = 0;
        home_devices_count = 0;
        cached_rooms_count = 0;
        active_remote_room_idx = 0;
        if (room_name && strlen(room_name) > 0) {
            strncpy(home_room_name, room_name, sizeof(home_room_name) - 1);
            home_room_name[sizeof(home_room_name) - 1] = '\\0';
        } else {
            strncpy(home_room_name, "Thiết Bị", sizeof(home_room_name));
        }"""

assert old_init in code_h, "old_init not found"
code_h = code_h.replace(old_init, new_init, 1)

old_set_title = """    void set_room_title(const char* room_name) {
        if (lbl_header_title && room_name) {
            lv_label_set_text_fmt(lbl_header_title, "NALA: %s", room_name);
        }
    }"""

new_set_title = """    void set_room_title(const char* room_name) {
        if (room_name && strlen(room_name) > 0) {
            strncpy(home_room_name, room_name, sizeof(home_room_name) - 1);
            home_room_name[sizeof(home_room_name) - 1] = '\\0';
            if (current_view_mode == VIEW_HOME_ROOM && lbl_header_title) {
                lv_label_set_text_fmt(lbl_header_title, "NALA: %s", home_room_name);
            }
        }
    }

    void set_room_view_timeout(uint8_t sec) {
        room_view_timeout_sec = sec;
        Serial.printf("[UI-ZERO-RAM] Room view timeout: %u sec\\n", (unsigned int)sec);
    }"""

assert old_set_title in code_h, "old_set_title not found"
code_h = code_h.replace(old_set_title, new_set_title, 1)

old_sync_funcs = """    void sync_buttons(const JsonArrayConst& btn_array) {
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
                chip_room_names[active_room_chips_count][sizeof(chip_room_names[0]) - 1] = '\\0';
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
    }"""

new_sync_funcs = """    void update_return_btn_label() {
        if (!lbl_home_return) return;
        char ret_txt[24] = "🏠 VỀ ";
        const char* last_space = strrchr(home_room_name, ' ');
        if (last_space && strlen(last_space) > 1) {
            strncat(ret_txt, last_space + 1, sizeof(ret_txt) - strlen(ret_txt) - 1);
        } else if (strlen(home_room_name) > 0) {
            strncat(ret_txt, home_room_name, sizeof(ret_txt) - strlen(ret_txt) - 1);
        } else {
            strncat(ret_txt, "PHÒNG", sizeof(ret_txt) - strlen(ret_txt) - 1);
        }
        for (char* p = ret_txt + 6; *p; ++p) *p = toupper(*p);
        lv_label_set_text(lbl_home_return, ret_txt);
    }

    void refresh_house_alert_status() {
        if (!lbl_house_alert) return;
        lv_label_set_text(lbl_house_alert, cached_house_summary);
        lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(cached_house_alert_color), 0);
        if (btn_master_off) {
            if (cached_has_active_devices) lv_obj_clear_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
            else lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);
        }
    }

    void render_current_view() {
        if (current_view_mode == VIEW_HOME_ROOM) {
            if (btn_home_return) lv_obj_add_flag(btn_home_return, LV_OBJ_FLAG_HIDDEN);

            if (chip_all) {
                lv_obj_set_style_bg_color(chip_all, lv_color_hex(0x0284C7), 0);
                lv_obj_set_style_border_color(chip_all, lv_color_hex(0x38BDF8), 0);
            }

            for (int i = 0; i < active_room_chips_count && i < MAX_ROOM_CHIPS; i++) {
                if (chip_rooms[i]) lv_obj_clear_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
            }

            if (lbl_header_title) {
                lv_label_set_text_fmt(lbl_header_title, "NALA: %s", home_room_name);
            }

            for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
                if (!buttons[i].btn_obj) continue;
                if (i < home_devices_count) {
                    buttons[i].id = home_devices_backup[i].id;
                    buttons[i].name = home_devices_backup[i].name;
                    buttons[i].entity_id = home_devices_backup[i].entity_id;
                    buttons[i].icon = home_devices_backup[i].icon;
                    buttons[i].room = home_room_name;
                    buttons[i].is_on = home_devices_backup[i].is_on;
                    buttons[i].temperature = home_devices_backup[i].temperature;
                    buttons[i].current_temperature = home_devices_backup[i].current_temperature;
                    buttons[i].hvac_mode = home_devices_backup[i].hvac_mode;
                    buttons[i].fan_mode = home_devices_backup[i].fan_mode;
                    buttons[i].swing_on = home_devices_backup[i].swing_on;
                    lv_obj_clear_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                    update_button_ui(i);
                } else {
                    lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                }
            }

            refresh_house_alert_status();
        }
        else if (current_view_mode == VIEW_ROOM_LIST) {
            if (btn_home_return) {
                update_return_btn_label();
                lv_obj_clear_flag(btn_home_return, LV_OBJ_FLAG_HIDDEN);
            }

            if (chip_all) {
                lv_obj_set_style_bg_color(chip_all, lv_color_hex(0xF59E0B), 0);
                lv_obj_set_style_border_color(chip_all, lv_color_hex(0xFCD34D), 0);
            }

            for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
                if (chip_rooms[i]) lv_obj_add_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
            }

            if (lbl_header_title) {
                lv_label_set_text(lbl_header_title, "NALA: TOÀN BỘ NHÀ");
            }

            if (lbl_house_alert) {
                lv_label_set_text(lbl_house_alert, "CHỌN PHÒNG ĐIỀU KHIỂN");
                lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0x38BDF8), 0);
            }
            if (btn_master_off) lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);

            for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
                if (!buttons[i].btn_obj) continue;
                if (i < cached_rooms_count) {
                    lv_obj_clear_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                    char btext[36];
                    if (cached_rooms[i].active_count > 0) {
                        snprintf(btext, sizeof(btext), "⚡ %s\\n(%d BẬT)", cached_rooms[i].name, cached_rooms[i].active_count);
                        lv_obj_set_style_bg_color(buttons[i].btn_obj, lv_color_hex(0x1C1917), 0);
                        lv_obj_set_style_border_color(buttons[i].btn_obj, lv_color_hex(0xF59E0B), 0);
                        lv_obj_set_style_text_color(buttons[i].lbl_obj, lv_color_hex(0xFEF08A), 0);
                    } else {
                        snprintf(btext, sizeof(btext), "%s\\n(Tắt)", cached_rooms[i].name);
                        lv_obj_set_style_bg_color(buttons[i].btn_obj, lv_color_hex(0x111927), 0);
                        lv_obj_set_style_border_color(buttons[i].btn_obj, lv_color_hex(0x27354A), 0);
                        lv_obj_set_style_text_color(buttons[i].lbl_obj, lv_color_hex(0x94A3B8), 0);
                    }
                    lv_label_set_text(buttons[i].lbl_obj, btext);
                } else {
                    lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                }
            }
        }
        else if (current_view_mode == VIEW_REMOTE_ROOM) {
            if (active_remote_room_idx >= cached_rooms_count) {
                return_to_home_room();
                return;
            }

            if (btn_home_return) {
                update_return_btn_label();
                lv_obj_clear_flag(btn_home_return, LV_OBJ_FLAG_HIDDEN);
            }

            if (chip_all) {
                lv_obj_set_style_bg_color(chip_all, lv_color_hex(0x111927), 0);
                lv_obj_set_style_border_color(chip_all, lv_color_hex(0x27354A), 0);
            }

            for (int i = 0; i < MAX_ROOM_CHIPS; i++) {
                if (chip_rooms[i]) lv_obj_add_flag(chip_rooms[i], LV_OBJ_FLAG_HIDDEN);
            }

            if (lbl_header_title) {
                lv_label_set_text_fmt(lbl_header_title, "NALA: %s (Từ xa)", cached_rooms[active_remote_room_idx].name);
            }

            if (lbl_house_alert) {
                if (room_view_timeout_sec > 0) {
                    char buf[32];
                    snprintf(buf, sizeof(buf), "⏳ Tự về sau %us", (unsigned int)room_view_timeout_sec);
                    lv_label_set_text(lbl_house_alert, buf);
                } else {
                    lv_label_set_text(lbl_house_alert, "Đang xem từ xa");
                }
                lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0xF59E0B), 0);
            }
            if (btn_master_off) lv_obj_add_flag(btn_master_off, LV_OBJ_FLAG_HIDDEN);

            uint8_t dcount = cached_rooms[active_remote_room_idx].devices_count;
            for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
                if (!buttons[i].btn_obj) continue;
                if (i < dcount) {
                    buttons[i].id = cached_rooms[active_remote_room_idx].devices[i].id;
                    buttons[i].name = cached_rooms[active_remote_room_idx].devices[i].name;
                    buttons[i].entity_id = cached_rooms[active_remote_room_idx].devices[i].entity_id;
                    buttons[i].icon = cached_rooms[active_remote_room_idx].devices[i].icon;
                    buttons[i].room = cached_rooms[active_remote_room_idx].name;
                    buttons[i].is_on = cached_rooms[active_remote_room_idx].devices[i].is_on;
                    buttons[i].temperature = cached_rooms[active_remote_room_idx].devices[i].temperature;
                    buttons[i].current_temperature = cached_rooms[active_remote_room_idx].devices[i].current_temperature;
                    buttons[i].hvac_mode = cached_rooms[active_remote_room_idx].devices[i].hvac_mode;
                    buttons[i].fan_mode = cached_rooms[active_remote_room_idx].devices[i].fan_mode;
                    buttons[i].swing_on = cached_rooms[active_remote_room_idx].devices[i].swing_on;
                    lv_obj_clear_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                    update_button_ui(i);
                } else {
                    lv_obj_add_flag(buttons[i].btn_obj, LV_OBJ_FLAG_HIDDEN);
                }
            }
        }
    }

    void enter_remote_room(int idx) {
        if (idx < 0 || idx >= cached_rooms_count) return;
        current_view_mode = VIEW_REMOTE_ROOM;
        active_remote_room_idx = idx;
        last_remote_touch_ms = millis();
        render_current_view();
    }

    void return_to_home_room() {
        if (current_view_mode == VIEW_HOME_ROOM) return;
        current_view_mode = VIEW_HOME_ROOM;
        render_current_view();
    }

    void tick_countdown(uint32_t now_ms) {
        if (current_view_mode != VIEW_REMOTE_ROOM) return;
        if (room_view_timeout_sec == 0) return;

        uint32_t elapsed_ms = now_ms - last_remote_touch_ms;
        uint32_t total_ms = (uint32_t)room_view_timeout_sec * 1000;

        if (elapsed_ms >= total_ms) {
            Serial.printf("[HUB-ZERO-RAM] Het %us timeout! Tu dong quay ve phong: %s\\n", 
                          (unsigned int)room_view_timeout_sec, home_room_name);
            return_to_home_room();
        } else {
            uint32_t remain_sec = (total_ms - elapsed_ms + 999) / 1000;
            static uint32_t last_disp_sec = 0xFFFFFFFF;
            if (remain_sec != last_disp_sec) {
                last_disp_sec = remain_sec;
                if (lbl_house_alert) {
                    char buf[32];
                    snprintf(buf, sizeof(buf), "⏳ Tự về sau %us", (unsigned int)remain_sec);
                    lv_label_set_text(lbl_house_alert, buf);
                    lv_obj_set_style_text_color(lbl_house_alert, lv_color_hex(0xF59E0B), 0);
                }
            }
        }
    }

    void sync_buttons(const JsonArrayConst& btn_array) {
        uint8_t count = btn_array.size();
        if (count > MAX_DASHBOARD_BUTTONS) count = MAX_DASHBOARD_BUTTONS;
        home_devices_count = count;

        for (uint8_t i = 0; i < count; i++) {
            const char* bid = btn_array[i]["id"] | "";
            strncpy(home_devices_backup[i].id, bid, sizeof(home_devices_backup[0].id) - 1);
            home_devices_backup[i].id[sizeof(home_devices_backup[0].id) - 1] = '\\0';

            const char* bname = btn_array[i]["name"] | "";
            strncpy(home_devices_backup[i].name, bname, sizeof(home_devices_backup[0].name) - 1);
            home_devices_backup[i].name[sizeof(home_devices_backup[0].name) - 1] = '\\0';

            const char* beid = btn_array[i]["entity_id"] | "";
            strncpy(home_devices_backup[i].entity_id, beid, sizeof(home_devices_backup[0].entity_id) - 1);
            home_devices_backup[i].entity_id[sizeof(home_devices_backup[0].entity_id) - 1] = '\\0';

            const char* bicon = btn_array[i]["icon"] | "light";
            strncpy(home_devices_backup[i].icon, bicon, sizeof(home_devices_backup[0].icon) - 1);
            home_devices_backup[i].icon[sizeof(home_devices_backup[0].icon) - 1] = '\\0';

            bool is_on = btn_array[i]["is_on"] | false;
            if (!is_on && btn_array[i].containsKey("state")) {
                String st = btn_array[i]["state"] | "off";
                is_on = (st == "on" || (st != "off" && st != "unavailable" && st != "unknown" && st.length() > 0));
            }
            home_devices_backup[i].is_on = is_on;

            if (btn_array[i].containsKey("attributes")) {
                JsonObjectConst attrs = btn_array[i]["attributes"];
                home_devices_backup[i].temperature = attrs["temperature"] | 26.0f;
                home_devices_backup[i].current_temperature = attrs["current_temperature"] | 28.0f;
                const char* hm = attrs["hvac_mode"] | "off";
                strncpy(home_devices_backup[i].hvac_mode, hm, sizeof(home_devices_backup[0].hvac_mode) - 1);
                home_devices_backup[i].hvac_mode[sizeof(home_devices_backup[0].hvac_mode) - 1] = '\\0';
                const char* fm = attrs["fan_mode"] | "auto";
                strncpy(home_devices_backup[i].fan_mode, fm, sizeof(home_devices_backup[0].fan_mode) - 1);
                home_devices_backup[i].fan_mode[sizeof(home_devices_backup[0].fan_mode) - 1] = '\\0';
                const char* sm = attrs["swing_mode"] | "";
                home_devices_backup[i].swing_on = (strlen(sm) > 0 && strcmp(sm, "off") != 0);
            }
        }

        if (current_view_mode == VIEW_HOME_ROOM) {
            render_current_view();
        }
    }

    void sync_house_status(const JsonObjectConst& house_st) {
        int on_lights = house_st["total_on_lights"] | 0;
        int on_fans = house_st["total_on_fans"] | 0;
        const char* summary = house_st["summary_text"] | "";
        if (summary && strlen(summary) > 0) {
            strncpy(cached_house_summary, summary, sizeof(cached_house_summary) - 1);
            cached_house_summary[sizeof(cached_house_summary) - 1] = '\\0';
        } else if (on_lights > 0 || on_fans > 0) {
            snprintf(cached_house_summary, sizeof(cached_house_summary), "%d ĐÈN & %d QUẠT BẬT", on_lights, on_fans);
        } else {
            strncpy(cached_house_summary, "ĐÃ TẮT HẾT CÁC PHÒNG", sizeof(cached_house_summary));
        }

        cached_has_active_devices = (on_lights > 0 || on_fans > 0);
        cached_house_alert_color = cached_has_active_devices ? 0xF59E0B : 0x10B981;

        if (current_view_mode == VIEW_HOME_ROOM) {
            refresh_house_alert_status();
        }
    }

    void sync_all_rooms(const JsonArrayConst& rooms_array) {
        uint8_t count = 0;
        for (JsonObjectConst r : rooms_array) {
            if (count >= MAX_CACHED_ROOMS) break;
            const char* rname = r["room_name"] | "";
            if (rname && strlen(rname) > 0) {
                strncpy(cached_rooms[count].name, rname, sizeof(cached_rooms[0].name) - 1);
                cached_rooms[count].name[sizeof(cached_rooms[0].name) - 1] = '\\0';
                const char* fl = r["floor"] | "";
                strncpy(cached_rooms[count].floor, fl, sizeof(cached_rooms[0].floor) - 1);
                cached_rooms[count].floor[sizeof(cached_rooms[0].floor) - 1] = '\\0';
                cached_rooms[count].active_count = r["active_devices_count"] | 0;
                cached_rooms[count].total_count = r["total_devices_count"] | 0;

                JsonArrayConst btns = r["buttons"];
                uint8_t bc = 0;
                for (JsonObjectConst b : btns) {
                    if (bc >= MAX_ROOM_DEVICES) break;
                    const char* bid = b["id"] | "";
                    strncpy(cached_rooms[count].devices[bc].id, bid, sizeof(cached_rooms[0].devices[0].id) - 1);
                    cached_rooms[count].devices[bc].id[sizeof(cached_rooms[0].devices[0].id) - 1] = '\\0';

                    const char* bname = b["name"] | "";
                    strncpy(cached_rooms[count].devices[bc].name, bname, sizeof(cached_rooms[0].devices[0].name) - 1);
                    cached_rooms[count].devices[bc].name[sizeof(cached_rooms[0].devices[0].name) - 1] = '\\0';

                    const char* beid = b["entity_id"] | "";
                    strncpy(cached_rooms[count].devices[bc].entity_id, beid, sizeof(cached_rooms[0].devices[0].entity_id) - 1);
                    cached_rooms[count].devices[bc].entity_id[sizeof(cached_rooms[0].devices[0].entity_id) - 1] = '\\0';

                    const char* bicon = b["icon"] | "light";
                    strncpy(cached_rooms[count].devices[bc].icon, bicon, sizeof(cached_rooms[0].devices[0].icon) - 1);
                    cached_rooms[count].devices[bc].icon[sizeof(cached_rooms[0].devices[0].icon) - 1] = '\\0';

                    bool is_on = b["is_on"] | false;
                    if (!is_on && b.containsKey("state")) {
                        String st = b["state"] | "off";
                        is_on = (st == "on" || (st != "off" && st != "unavailable" && st != "unknown" && st.length() > 0));
                    }
                    cached_rooms[count].devices[bc].is_on = is_on;

                    if (b.containsKey("attributes")) {
                        JsonObjectConst attrs = b["attributes"];
                        cached_rooms[count].devices[bc].temperature = attrs["temperature"] | 26.0f;
                        cached_rooms[count].devices[bc].current_temperature = attrs["current_temperature"] | 28.0f;
                        const char* hm = attrs["hvac_mode"] | "off";
                        strncpy(cached_rooms[count].devices[bc].hvac_mode, hm, sizeof(cached_rooms[0].devices[0].hvac_mode) - 1);
                        cached_rooms[count].devices[bc].hvac_mode[sizeof(cached_rooms[0].devices[0].hvac_mode) - 1] = '\\0';
                        const char* fm = attrs["fan_mode"] | "auto";
                        strncpy(cached_rooms[count].devices[bc].fan_mode, fm, sizeof(cached_rooms[0].devices[0].fan_mode) - 1);
                        cached_rooms[count].devices[bc].fan_mode[sizeof(cached_rooms[0].devices[0].fan_mode) - 1] = '\\0';
                        const char* sm = attrs["swing_mode"] | "";
                        cached_rooms[count].devices[bc].swing_on = (strlen(sm) > 0 && strcmp(sm, "off") != 0);
                    }
                    bc++;
                }
                cached_rooms[count].devices_count = bc;
                count++;
            }
        }
        cached_rooms_count = count;

        if (current_view_mode == VIEW_ROOM_LIST) {
            render_current_view();
        } else if (current_view_mode == VIEW_REMOTE_ROOM && active_remote_room_idx < cached_rooms_count) {
            render_current_view();
        }
    }"""

assert old_sync_funcs in code_h, "old_sync_funcs not found"
code_h = code_h.replace(old_sync_funcs, new_sync_funcs, 1)

old_build_chips = """        lbl_chip_all = lv_label_create(chip_all);
        lv_obj_clear_flag(lbl_chip_all, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_chip_all, "TOÀN NHÀ");
        lv_obj_set_style_text_font(lbl_chip_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_chip_all);

        int chip_x = 78;"""

new_build_chips = """        lbl_chip_all = lv_label_create(chip_all);
        lv_obj_clear_flag(lbl_chip_all, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_chip_all, "TOÀN NHÀ");
        lv_obj_set_style_text_font(lbl_chip_all, &font_vietnamese_14, 0);
        lv_obj_center(lbl_chip_all);

        // Nút VỀ PHÒNG CHÍNH - nằm cạnh nút TOÀN NHÀ
        btn_home_return = lv_btn_create(cont_room_chips);
        lv_obj_set_size(btn_home_return, 88, 24);
        lv_obj_set_pos(btn_home_return, 78, 2);
        lv_obj_set_style_radius(btn_home_return, 12, 0);
        lv_obj_set_style_bg_color(btn_home_return, lv_color_hex(0x059669), 0);
        lv_obj_set_style_border_color(btn_home_return, lv_color_hex(0x34D399), 0);
        lv_obj_set_style_border_width(btn_home_return, 1, 0);
        lv_obj_set_style_pad_all(btn_home_return, 1, 0);
        lv_obj_add_event_cb(btn_home_return, event_handler_trampoline, LV_EVENT_CLICKED, this);

        lbl_home_return = lv_label_create(btn_home_return);
        lv_obj_clear_flag(lbl_home_return, LV_OBJ_FLAG_CLICKABLE);
        lv_label_set_text(lbl_home_return, "🏠 VỀ PHÒNG");
        lv_obj_set_style_text_font(lbl_home_return, &font_vietnamese_14, 0);
        lv_obj_center(lbl_home_return);
        lv_obj_add_flag(btn_home_return, LV_OBJ_FLAG_HIDDEN);

        int chip_x = 78;"""

assert old_build_chips in code_h, "old_build_chips not found"
code_h = code_h.replace(old_build_chips, new_build_chips, 1)

old_handle_events = """        // Room filter chips
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
                Serial.printf("[UI-ACTION] Clicked Button %d (%s) entity=%s is_on=%d\\n", 
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
        }"""

new_handle_events = """        // Zero-RAM Smart Floor & Room Navigation Events
        if (target == chip_all && code == LV_EVENT_CLICKED) {
            Serial.println("[UI-ACTION] Clicked TOÀN NHÀ button!");
            if (current_view_mode == VIEW_HOME_ROOM) {
                current_view_mode = VIEW_ROOM_LIST;
                render_current_view();
            } else {
                return_to_home_room();
            }
            return;
        }

        if (target == btn_home_return && code == LV_EVENT_CLICKED) {
            Serial.println("[UI-ACTION] Clicked Return to Home Room button!");
            return_to_home_room();
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

        // Device buttons (reused for Room List & Devices)
        for (int i = 0; i < MAX_DASHBOARD_BUTTONS; i++) {
            if (target == buttons[i].btn_obj && code == LV_EVENT_CLICKED) {
                if (current_view_mode == VIEW_ROOM_LIST) {
                    if (i < cached_rooms_count) {
                        Serial.printf("[UI-ACTION] Selected room %d: %s\\n", i, cached_rooms[i].name);
                        if (strcasecmp(cached_rooms[i].name, home_room_name) == 0) {
                            return_to_home_room();
                        } else {
                            enter_remote_room(i);
                        }
                    }
                    return;
                }

                if (current_view_mode == VIEW_REMOTE_ROOM) {
                    last_remote_touch_ms = millis();
                    if (active_remote_room_idx < cached_rooms_count && i < cached_rooms[active_remote_room_idx].devices_count) {
                        cached_rooms[active_remote_room_idx].devices[i].is_on = !buttons[i].is_on;
                    }
                }

                Serial.printf("[UI-ACTION] Clicked Button %d (%s) entity=%s is_on=%d\\n", 
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
        }"""

assert old_handle_events in code_h, "old_handle_events not found"
code_h = code_h.replace(old_handle_events, new_handle_events, 1)

with open(path_h, 'w', encoding='utf-8') as f:
    f.write(code_h)

print("Successfully patched ui_lvgl_dashboard.h with Zero-RAM architecture!")


# -------------------------------------------------------------
# 2. PATCH MAIN.CPP
# -------------------------------------------------------------
path_cpp = 'firmware_esp32s3_panel/src/main.cpp'
with open(path_cpp, 'r', encoding='utf-8') as f:
    code_cpp = f.read()

old_cpp_ver = '#define CURRENT_FIRMWARE_VERSION "v3.2.1"'
new_cpp_ver = '#define CURRENT_FIRMWARE_VERSION "v3.3.1"'
assert old_cpp_ver in code_cpp, "old_cpp_ver not found"
code_cpp = code_cpp.replace(old_cpp_ver, new_cpp_ver, 1)

old_cpp_settings = """            if (st.containsKey("ai_model")) {
                const char* aim = st["ai_model"] | "gemini";
                if (strcmp(nvsStore.get().ai_model, aim) != 0) {
                    strncpy(nvsStore.get().ai_model, aim, sizeof(nvsStore.get().ai_model));
                    changed = true;
                }
            }"""

new_cpp_settings = """            if (st.containsKey("ai_model")) {
                const char* aim = st["ai_model"] | "gemini";
                if (strcmp(nvsStore.get().ai_model, aim) != 0) {
                    strncpy(nvsStore.get().ai_model, aim, sizeof(nvsStore.get().ai_model));
                    changed = true;
                }
            }
            if (st.containsKey("room_view_timeout")) {
                uint8_t to = st["room_view_timeout"] | 15;
                if (to != nvsStore.get().room_view_timeout) {
                    nvsStore.get().room_view_timeout = to;
                    changed = true;
                }
                if (taken) {
                    uiDashboard.set_room_view_timeout(to);
                }
            }"""

assert old_cpp_settings in code_cpp, "old_cpp_settings not found"
code_cpp = code_cpp.replace(old_cpp_settings, new_cpp_settings, 1)

old_cpp_task = """                uiDashboard.check_flush_climate_setpoint();
                lv_timer_handler();"""

new_cpp_task = """                uiDashboard.check_flush_climate_setpoint();
                uiDashboard.tick_countdown(millis());
                lv_timer_handler();"""

assert old_cpp_task in code_cpp, "old_cpp_task not found"
code_cpp = code_cpp.replace(old_cpp_task, new_cpp_task, 1)

old_cpp_init = """            uiDashboard.init(
                nvsStore.get().room_name,
                WiFi.localIP().toString().c_str(),
                pairing_code.c_str(),
                nvsStore.get().speaker_volume,
                nvsStore.get().lcd_brightness,
                nvsStore.get().ring_on_call,
                nvsStore.get_mic_gain()
            );"""

new_cpp_init = """            uiDashboard.init(
                nvsStore.get().room_name,
                WiFi.localIP().toString().c_str(),
                pairing_code.c_str(),
                nvsStore.get().speaker_volume,
                nvsStore.get().lcd_brightness,
                nvsStore.get().ring_on_call,
                nvsStore.get_mic_gain()
            );
            uiDashboard.set_room_view_timeout(nvsStore.get().room_view_timeout);"""

assert old_cpp_init in code_cpp, "old_cpp_init not found"
code_cpp = code_cpp.replace(old_cpp_init, new_cpp_init, 1)

with open(path_cpp, 'w', encoding='utf-8') as f:
    f.write(code_cpp)

print("Successfully patched main.cpp with v3.3.1 Zero-RAM!")
