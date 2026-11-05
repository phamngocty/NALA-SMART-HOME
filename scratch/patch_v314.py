import re

# 1. Patch main.cpp
path_main = r'firmware_esp32s3_panel\src\main.cpp'
with open(path_main, 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

# Bump version to v3.1.4
assert '#define CURRENT_FIRMWARE_VERSION "v3.1.3"' in c
c = c.replace('#define CURRENT_FIRMWARE_VERSION "v3.1.3"', '#define CURRENT_FIRMWARE_VERSION "v3.1.4"')

# Replace read_touch_calibrated and my_touchpad_read with clean Single Burst Read (5 bytes)
old_touch_code = '''// Hàm đọc 1 byte từ thanh ghi FT6336 với Repeated Start chuẩn xác (aselectroworks)
static uint8_t ft_read_reg_byte(uint8_t reg) {
    Wire.beginTransmission(0x38);
    Wire.write(reg);
    Wire.endTransmission(false);
    if (Wire.requestFrom((uint16_t)0x38, (uint8_t)1) == 1) {
        return Wire.read();
    }
    return 0xFF;
}

// Đọc tọa độ cảm ứng điện dung FT6336 đảo 180° chuẩn xác đã kiểm chứng 100%
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
}

static int16_t last_touch_x = 0;
static int16_t last_touch_y = 0;
static bool was_pressed = false;

void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
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

new_touch_code = '''// Đọc tọa độ cảm ứng điện dung FT6336 đảo 180° chuẩn xác - Single Burst Read 5 bytes
bool read_touch_calibrated(int16_t *x, int16_t *y) {
    if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(10)) == pdTRUE) {
        Wire.beginTransmission(0x38);
        Wire.write(0x02); // Start register: TD_STATUS
        uint8_t err = Wire.endTransmission();
        if (err == 0 && Wire.requestFrom((uint16_t)0x38, (uint8_t)5) == 5) {
            uint8_t points = Wire.read() & 0x0F;
            if (points >= 1 && points <= 2) {
                uint8_t x_high = Wire.read();
                uint8_t x_low  = Wire.read();
                uint8_t y_high = Wire.read();
                uint8_t y_low  = Wire.read();
                int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
                int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;
                *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                xSemaphoreGive(i2c_mutex);
                return true;
            }
        }
        xSemaphoreGive(i2c_mutex);
    }
    return false;
}

static int16_t last_touch_x = 0;
static int16_t last_touch_y = 0;
static bool was_pressed = false;

void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
    int16_t x = 0, y = 0;
    if (read_touch_calibrated(&x, &y)) {
        data->state = LV_INDEV_STATE_PR;
        data->point.x = x;
        data->point.y = y;
        last_touch_x = x;
        last_touch_y = y;
        if (!was_pressed) {
            was_pressed = true;
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

assert old_touch_code in c, "old_touch_code not found in main.cpp!"
c = c.replace(old_touch_code, new_touch_code, 1)

with open(path_main, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c)
print("Updated main.cpp to v3.1.4 successfully!")

# 2. Patch ui_lvgl_dashboard.h
path_ui = r'firmware_esp32s3_panel\include\ui_lvgl_dashboard.h'
with open(path_ui, 'r', encoding='utf-8') as f:
    u = f.read().replace('\r\n', '\n')

old_log = 'Serial.printf("[UI-EVENT] code=%d target=%p cur=%p\\n", (int)code, target, cur_target);'
new_log = '''if (code == LV_EVENT_CLICKED) {
            Serial.printf("[UI-EVENT] CLICKED target=%p cur=%p\\n", target, cur_target);
        } else if (code == LV_EVENT_VALUE_CHANGED) {
            Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p cur=%p\\n", target, cur_target);
        }'''

assert old_log in u, "old_log not found in ui_lvgl_dashboard.h!"
u = u.replace(old_log, new_log, 1)

with open(path_ui, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(u)
print("Updated ui_lvgl_dashboard.h successfully!")
