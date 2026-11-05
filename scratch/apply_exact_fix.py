import os

# 1. Update main.cpp
path_main = r'firmware_esp32s3_panel\src\main.cpp'
with open(path_main, 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Restore LGFX_Panel to clean SPI (remove _touch_instance to avoid setPins conflict)
old_class_with_touch = '''class LGFX_Panel : public lgfx::LGFX_Device {
    lgfx::Panel_ILI9341 _panel_instance;
    lgfx::Bus_SPI       _bus_instance;
    lgfx::Light_PWM     _light_instance;
    lgfx::Touch_FT5x06  _touch_instance;

public:
    LGFX_Panel() {
        {
            auto cfg = _bus_instance.config();
            cfg.spi_host = LCD_SPI_HOST;
            cfg.spi_mode = 0;
            cfg.freq_write = 40000000;
            cfg.freq_read  = 16000000;
            cfg.spi_3wire  = false;
            cfg.use_lock   = true;
            cfg.dma_channel = SPI_DMA_CH_AUTO;
            cfg.pin_sclk   = LCD_SPI_SCLK_PIN; // GPIO 12
            cfg.pin_mosi   = LCD_SPI_MOSI_PIN; // GPIO 11
            cfg.pin_miso   = LCD_SPI_MISO_PIN; // GPIO 13
            cfg.pin_dc     = LCD_SPI_DC_PIN;   // GPIO 46
            _bus_instance.config(cfg);
            _panel_instance.setBus(&_bus_instance);
        }
        {
            auto cfg = _panel_instance.config();
            cfg.pin_cs           = LCD_SPI_CS_PIN; // GPIO 10
            cfg.pin_rst          = -1;
            cfg.pin_busy         = -1;
            cfg.panel_width      = LCD_WIDTH;
            cfg.panel_height     = LCD_HEIGHT;
            cfg.offset_x         = 0;
            cfg.offset_y         = 0;
            cfg.offset_rotation  = 0;
            cfg.readable         = true;
            cfg.invert           = true;  // ST7789/IPS Panel: BẮT BUỘC INVERT ĐỂ MÀU KHÔNG BỊ ÂM BẢN (Nền đen sâu Apple Glass)
            cfg.rgb_order        = false;
            cfg.dlen_16bit       = false;
            cfg.bus_shared       = true;
            _panel_instance.config(cfg);
        }
        {
            auto cfg = _light_instance.config();
            cfg.pin_bl      = LCD_BL_PIN; // GPIO 45
            cfg.invert      = false;
            cfg.freq        = LCD_BL_PWM_FREQ;
            cfg.pwm_channel = LCD_BL_PWM_CHANNEL;
            _light_instance.config(cfg);
            _panel_instance.setLight(&_light_instance);
        }
        {
            auto cfg = _touch_instance.config();
            cfg.x_min = 0;
            cfg.x_max = LCD_WIDTH - 1;
            cfg.y_min = 0;
            cfg.y_max = LCD_HEIGHT - 1;
            cfg.pin_int = TOUCH_INT_PIN; // GPIO 17
            cfg.bus_shared = true;
            cfg.offset_rotation = 2; // Đảo cả 2 trục 180° chuẩn xác tuyệt đối!
            cfg.i2c_port = 0;
            cfg.i2c_addr = I2C_ADDR_FT6336U;
            cfg.pin_sda = I2C_PORT_SDA_PIN; // GPIO 16
            cfg.pin_scl = I2C_PORT_SCL_PIN; // GPIO 15
            cfg.freq = 400000;
            _touch_instance.config(cfg);
            _panel_instance.setTouch(&_touch_instance);
        }
        setPanel(&_panel_instance);
    }
};'''

clean_class = '''class LGFX_Panel : public lgfx::LGFX_Device {
    lgfx::Panel_ILI9341 _panel_instance;
    lgfx::Bus_SPI       _bus_instance;
    lgfx::Light_PWM     _light_instance;

public:
    LGFX_Panel() {
        {
            auto cfg = _bus_instance.config();
            cfg.spi_host = LCD_SPI_HOST;
            cfg.spi_mode = 0;
            cfg.freq_write = 40000000;
            cfg.freq_read  = 16000000;
            cfg.spi_3wire  = false;
            cfg.use_lock   = true;
            cfg.dma_channel = SPI_DMA_CH_AUTO;
            cfg.pin_sclk   = LCD_SPI_SCLK_PIN; // GPIO 12
            cfg.pin_mosi   = LCD_SPI_MOSI_PIN; // GPIO 11
            cfg.pin_miso   = LCD_SPI_MISO_PIN; // GPIO 13
            cfg.pin_dc     = LCD_SPI_DC_PIN;   // GPIO 46
            _bus_instance.config(cfg);
            _panel_instance.setBus(&_bus_instance);
        }
        {
            auto cfg = _panel_instance.config();
            cfg.pin_cs           = LCD_SPI_CS_PIN; // GPIO 10
            cfg.pin_rst          = -1;
            cfg.pin_busy         = -1;
            cfg.panel_width      = LCD_WIDTH;
            cfg.panel_height     = LCD_HEIGHT;
            cfg.offset_x         = 0;
            cfg.offset_y         = 0;
            cfg.offset_rotation  = 0;
            cfg.readable         = true;
            cfg.invert           = true;  // ST7789/IPS Panel: BẮT BUỘC INVERT ĐỂ MÀU KHÔNG BỊ ÂM BẢN (Nền đen sâu Apple Glass)
            cfg.rgb_order        = false;
            cfg.dlen_16bit       = false;
            cfg.bus_shared       = true;
            _panel_instance.config(cfg);
        }
        {
            auto cfg = _light_instance.config();
            cfg.pin_bl      = LCD_BL_PIN; // GPIO 45
            cfg.invert      = false;
            cfg.freq        = LCD_BL_PWM_FREQ;
            cfg.pwm_channel = LCD_BL_PWM_CHANNEL;
            _light_instance.config(cfg);
            _panel_instance.setLight(&_light_instance);
        }
        setPanel(&_panel_instance);
    }
};'''

assert old_class_with_touch in c, "old_class_with_touch not found in main.cpp!"
c = c.replace(old_class_with_touch, clean_class, 1)

# Direct read_touch_calibrated matching test_touch_hardware
old_read_touch = '''// Đọc tọa độ cảm ứng kết hợp LovyanGFX chuẩn + Fallback INT Pin
bool read_touch_calibrated(int16_t *x, int16_t *y) {
    // 1. Ưu tiên driver phần cứng chuẩn của LovyanGFX (Đã xoay 180° và lọc nhiễu chuẩn xác)
    uint16_t tx = 0, ty = 0;
    if (tft.getTouch(&tx, &ty)) {
        *x = (int16_t)tx;
        *y = (int16_t)ty;
        static unsigned long last_dbg = 0;
        if (millis() - last_dbg > 150) {
            last_dbg = millis();
            Serial.printf("[TOUCH-LGFX] Matched -> (%d, %d)\\n", *x, *y);
        }
        return true;
    }

    // 2. Fallback trực tiếp: nếu INT kéo xuống 0 mà LGFX chưa đọc kịp
    if (digitalRead(TOUCH_INT_PIN) == LOW) {
        if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
            uint8_t points = ft_read_reg_byte(0x02) & 0x0F;
            if (points >= 1 && points <= 2) {
                uint8_t x_high = ft_read_reg_byte(0x03);
                uint8_t x_low  = ft_read_reg_byte(0x04);
                uint8_t y_high = ft_read_reg_byte(0x05);
                uint8_t y_low  = ft_read_reg_byte(0x06);
                int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
                int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;
                *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                static unsigned long last_fb = 0;
                if (millis() - last_fb > 150) {
                    last_fb = millis();
                    Serial.printf("[TOUCH-FB] INT Fallback -> (%d, %d)\\n", *x, *y);
                }
                xSemaphoreGive(i2c_mutex);
                return true;
            }
            xSemaphoreGive(i2c_mutex);
        }
    }
    return false;
}'''

new_read_touch = '''// Đọc tọa độ cảm ứng điện dung FT6336 đảo 180° chuẩn xác đã kiểm chứng 100%
bool read_touch_calibrated(int16_t *x, int16_t *y) {
    if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(15)) == pdTRUE) {
        uint8_t points = ft_read_reg_byte(0x02) & 0x0F;
        if (points >= 1 && points <= 2) {
            uint8_t x_high = ft_read_reg_byte(0x03);
            uint8_t x_low  = ft_read_reg_byte(0x04);
            uint8_t y_high = ft_read_reg_byte(0x05);
            uint8_t y_low  = ft_read_reg_byte(0x06);
            int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
            int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;
            *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
            *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
            xSemaphoreGive(i2c_mutex);
            return true;
        }
        xSemaphoreGive(i2c_mutex);
    }
    return false;
}'''

assert old_read_touch in c, "old_read_touch not found in main.cpp!"
c = c.replace(old_read_touch, new_read_touch, 1)

# my_touchpad_read with clear logs
old_indev_read = '''void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
    int16_t x = 0, y = 0;
    if (read_touch_calibrated(&x, &y)) {
        data->state = LV_INDEV_STATE_PR;
        data->point.x = x;
        data->point.y = y;
        last_touch_x = x;
        last_touch_y = y;
        was_pressed = true;
    } else {
        data->state = LV_INDEV_STATE_REL;
        data->point.x = last_touch_x;
        data->point.y = last_touch_y;
        if (was_pressed) {
            was_pressed = false;
            Serial.printf("[TOUCH] Released at (%d, %d)\\n", last_touch_x, last_touch_y);
        }
    }
}'''

new_indev_read = '''void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
    int16_t x = 0, y = 0;
    if (read_touch_calibrated(&x, &y)) {
        data->state = LV_INDEV_STATE_PR;
        data->point.x = x;
        data->point.y = y;
        last_touch_x = x;
        last_touch_y = y;
        was_pressed = true;
        static unsigned long last_pr_log = 0;
        if (millis() - last_pr_log > 100) {
            last_pr_log = millis();
            Serial.printf("[LVGL-INDEV] PRESSED at (%d, %d)\\n", x, y);
        }
    } else {
        data->state = LV_INDEV_STATE_REL;
        data->point.x = last_touch_x;
        data->point.y = last_touch_y;
        if (was_pressed) {
            was_pressed = false;
            Serial.printf("[LVGL-INDEV] RELEASED at (%d, %d)\\n", last_touch_x, last_touch_y);
        }
    }
}'''

assert old_indev_read in c, "old_indev_read not found in main.cpp!"
c = c.replace(old_indev_read, new_indev_read, 1)

c = c.replace('#define CURRENT_FIRMWARE_VERSION "v3.1.2"', '#define CURRENT_FIRMWARE_VERSION "v3.1.3"')

with open(path_main, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c)

print("Updated main.cpp to v3.1.3 successfully!")

# 2. Update ui_lvgl_dashboard.h to log all UI events
path_ui = r'firmware_esp32s3_panel\include\ui_lvgl_dashboard.h'
with open(path_ui, 'r', encoding='utf-8') as f:
    u = f.read().replace('\r\n', '\n')

old_handle_event_start = '''    void handle_event(lv_event_t* e) {
        lv_event_code_t code = lv_event_get_code(e);
        lv_obj_t* target = lv_event_get_target(e);
        lv_obj_t* cur_target = lv_event_get_current_target(e);'''

new_handle_event_start = '''    void handle_event(lv_event_t* e) {
        lv_event_code_t code = lv_event_get_code(e);
        lv_obj_t* target = lv_event_get_target(e);
        lv_obj_t* cur_target = lv_event_get_current_target(e);
        Serial.printf("[UI-EVENT] code=%d target=%p cur=%p\\n", (int)code, target, cur_target);'''

assert old_handle_event_start in u, "old_handle_event_start not found in ui_lvgl_dashboard.h!"
u = u.replace(old_handle_event_start, new_handle_event_start, 1)

with open(path_ui, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(u)

print("Updated ui_lvgl_dashboard.h successfully!")
