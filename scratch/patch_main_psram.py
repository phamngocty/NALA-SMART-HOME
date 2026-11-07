with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update version to v3.4.0
content = content.replace(
    '#define CURRENT_FIRMWARE_VERSION "v3.3.6"',
    '#define CURRENT_FIRMWARE_VERSION "v3.4.0"'
)

# 2. Update buffer declarations
old_bufs = """static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf1[LCD_WIDTH * 40];
static lv_color_t buf2[LCD_WIDTH * 40];
static lv_disp_drv_t disp_drv;"""

new_bufs = """static lv_disp_draw_buf_t draw_buf;
static lv_color_t* buf1 = nullptr;
static lv_color_t* buf2 = nullptr;
static lv_color_t buf_fallback[LCD_WIDTH * 20];
static lv_disp_drv_t disp_drv;"""

content = content.replace(old_bufs, new_bufs)

# 3. Update buffer initialization in setup
old_init = """            // Khởi tạo LVGL 8.3.11
            lv_init();
            lv_disp_draw_buf_init(&draw_buf, buf1, buf2, LCD_WIDTH * 40);"""

new_init = """            // Khởi tạo LVGL 8.3.11
            lv_init();
            if (psramFound()) {
                size_t lines = 80;
                buf1 = (lv_color_t*) ps_malloc(LCD_WIDTH * lines * sizeof(lv_color_t));
                buf2 = (lv_color_t*) ps_malloc(LCD_WIDTH * lines * sizeof(lv_color_t));
                if (buf1 && buf2) {
                    lv_disp_draw_buf_init(&draw_buf, buf1, buf2, LCD_WIDTH * lines);
                    Serial.printf("[LVGL-PSRAM] Initialized Double Buffering in PSRAM (2x %u lines, %u KB)\\n",
                                  (unsigned int)lines, (unsigned int)(2 * LCD_WIDTH * lines * sizeof(lv_color_t) / 1024));
                }
            }
            if (!buf1 || !buf2) {
                lv_disp_draw_buf_init(&draw_buf, buf_fallback, NULL, LCD_WIDTH * 20);
                Serial.println("[LVGL] Using fallback internal SRAM single buffer");
            }"""

content = content.replace(old_init, new_init)

with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated main.cpp for v3.4.0 with PSRAM Double Buffer!")
