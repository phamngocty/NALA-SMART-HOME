import sys

with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace set_ai_state and set_ai_sentence
old_block = """    void set_ai_state(const char* state_str, const char* text = nullptr) {
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

    // Hiển thị từng câu âm thanh đang nói & đổi biểu cảm khuôn mặt sống động (Xiaozhi Style)
    void set_ai_sentence(const char* sentence) {
        if (lbl_ai_state) {
            lv_label_set_text(lbl_ai_state, "AI: Đang nói...");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
        }
        if (ai_pulse_circle) {
            lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x059669), 0);
            lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x34D399), 0);
        }
        if (lbl_ai_avatar) {
            static bool blink_toggle = false;
            blink_toggle = !blink_toggle;
            lv_label_set_text(lbl_ai_avatar, blink_toggle ? "(^‿^)" : "(•_~)");
        }
        if (sentence && strlen(sentence) > 0) {
            set_ai_text(sentence);
        }
    }"""

new_block = """    void set_ai_state(const char* state_str, const char* text = nullptr) {
        if (lbl_ai_state && state_str) {
            if (strcasecmp(state_str, "listening") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang nghe...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x38BDF8), 0);
                if (ai_pulse_circle) {
                    lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0369A1), 0);
                    lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x38BDF8), 0);
                }
                if (lbl_ai_avatar) lv_label_set_text(lbl_ai_avatar, "(◕ ‿ ◕)");
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "🟢 ĐANG NGHE (NÓI TỰ NHIÊN)");
            } else if (strcasecmp(state_str, "processing") == 0 || strcasecmp(state_str, "thinking") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang suy nghĩ...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0xF59E0B), 0);
                if (ai_pulse_circle) {
                    lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x78350F), 0);
                    lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0xF59E0B), 0);
                }
                if (lbl_ai_avatar) lv_label_set_text(lbl_ai_avatar, "( • _ • )");
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "⏳ ĐANG SUY NGHĨ...");
            } else if (strcasecmp(state_str, "speaking") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Đang trả lời...");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
                if (ai_pulse_circle) {
                    lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x064E3B), 0);
                    lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x34D399), 0);
                }
                if (lbl_ai_avatar) lv_label_set_text(lbl_ai_avatar, "(^ ‿ ^)");
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "🔊 CHẠM ĐỂ NGẮT LỜI");
            } else if (strcasecmp(state_str, "goodbye") == 0) {
                lv_label_set_text(lbl_ai_state, "AI: Tạm biệt bạn!");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0xC084FC), 0);
                if (ai_pulse_circle) {
                    lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x581C87), 0);
                    lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0xC084FC), 0);
                }
                if (lbl_ai_avatar) lv_label_set_text(lbl_ai_avatar, "(^ ‿ ^)ﾉ");
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "👋 HẸN GẶP LẠI!");
            } else {
                lv_label_set_text(lbl_ai_state, "AI: Sẵn sàng (Hey Nala)");
                lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x94A3B8), 0);
                if (ai_pulse_circle) {
                    lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0F172A), 0);
                    lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x334155), 0);
                }
                if (lbl_ai_avatar) lv_label_set_text(lbl_ai_avatar, "(- ‿ -)");
                if (lbl_ai_ptt_text) lv_label_set_text(lbl_ai_ptt_text, "GIỮ ĐỂ NÓI VỚI NALA AI");
            }
        }
        if (text && strlen(text) > 0) {
            set_ai_text(text);
        }
    }

    // Hiển thị từng câu âm thanh đang nói & đổi biểu cảm khuôn mặt sống động (Xiaozhi Style)
    void set_ai_sentence(const char* sentence) {
        if (lbl_ai_state) {
            lv_label_set_text(lbl_ai_state, "AI: Đang nói...");
            lv_obj_set_style_text_color(lbl_ai_state, lv_color_hex(0x10B981), 0);
        }
        if (ai_pulse_circle) {
            lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x064E3B), 0);
            lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x34D399), 0);
        }
        if (lbl_ai_avatar) {
            static bool blink_toggle = false;
            blink_toggle = !blink_toggle;
            lv_label_set_text(lbl_ai_avatar, blink_toggle ? "(^ ‿ ^)" : "(• ‿ •)");
        }
        if (sentence && strlen(sentence) > 0) {
            set_ai_text(sentence);
        }
    }"""

if old_block in content:
    content = content.replace(old_block, new_block)
    print("Replaced set_ai_state and set_ai_sentence successfully!")
else:
    print("Warning: old_block not found exactly!")

# Update ai_pulse_circle styling in build_tab_ai
old_pulse = """        ai_pulse_circle = lv_obj_create(tab_ai);
        lv_obj_set_size(ai_pulse_circle, 44, 44);
        lv_obj_align(ai_pulse_circle, LV_ALIGN_TOP_MID, 0, 24);
        lv_obj_set_style_radius(ai_pulse_circle, LV_RADIUS_CIRCLE, 0);
        lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0369A1), 0);
        lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x38BDF8), 0);
        lv_obj_set_style_border_width(ai_pulse_circle, 2, 0);

        lbl_ai_avatar = lv_label_create(ai_pulse_circle);
        lv_obj_t* lbl_orb = lbl_ai_avatar;
        lv_label_set_text(lbl_orb, "NALA");
        lv_obj_set_style_text_font(lbl_orb, &font_vietnamese_14, 0);
        lv_obj_set_style_text_color(lbl_orb, lv_color_hex(0xFFFFFF), 0);
        lv_obj_center(lbl_orb);"""

new_pulse = """        ai_pulse_circle = lv_obj_create(tab_ai);
        lv_obj_set_size(ai_pulse_circle, 96, 44);
        lv_obj_align(ai_pulse_circle, LV_ALIGN_TOP_MID, 0, 24);
        lv_obj_set_style_radius(ai_pulse_circle, 22, 0);
        lv_obj_set_style_bg_color(ai_pulse_circle, lv_color_hex(0x0F172A), 0);
        lv_obj_set_style_border_color(ai_pulse_circle, lv_color_hex(0x334155), 0);
        lv_obj_set_style_border_width(ai_pulse_circle, 2, 0);

        lbl_ai_avatar = lv_label_create(ai_pulse_circle);
        lv_label_set_text(lbl_ai_avatar, "(- ‿ -)");
        lv_obj_set_style_text_font(lbl_ai_avatar, &font_vietnamese_16, 0);
        lv_obj_set_style_text_color(lbl_ai_avatar, lv_color_hex(0x38BDF8), 0);
        lv_obj_center(lbl_ai_avatar);"""

if old_pulse in content:
    content = content.replace(old_pulse, new_pulse)
    print("Replaced ai_pulse_circle styling successfully!")
else:
    print("Warning: old_pulse not found exactly!")

with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'w', encoding='utf-8') as f:
    f.write(content)
print("Finished patching ui_lvgl_dashboard.h")
