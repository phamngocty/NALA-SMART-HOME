import sys

with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    text = f.read()

start1 = text.find('static uint8_t global_touch_mode = 0;')
end1 = text.find('// 3. UI ACTION CALLBACKS', start1)
assert start1 != -1 and end1 != -1, f"start1={start1}, end1={end1}"

new_touch_block = """static uint8_t global_touch_mode = 0; // 0: Both Inverted (chuan 100%), 1: Direct raw, 2: Invert X, 3: Invert Y, 4-7: Swapped axes

void set_touch_calib_mode(uint8_t m) {
    global_touch_mode = m % 8;
    const char* mode_desc[] = {
        "Both inverted (chuan)",
        "Direct raw",
        "Invert X",
        "Invert Y",
        "Swapped axes",
        "Swapped + Invert X",
        "Swapped + Invert Y",
        "Swapped + Both inverted"
    };
    Serial.printf("[TOUCH-CALIB] Switched to mode %d: %s\\n", global_touch_mode, mode_desc[global_touch_mode]);
}

// Đọc tọa độ cảm ứng điện dung FT6336G / CST816S đảo 180° chuẩn xác
bool read_touch_calibrated(int16_t *x, int16_t *y) {
    if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(15)) != pdTRUE) {
        return false;
    }

    if (active_touch_addr == 0x00) {
        uint8_t addrs[] = { 0x38, 0x15, 0x1A, 0x5D };
        for (uint8_t a : addrs) {
            Wire.beginTransmission(a);
            if (Wire.endTransmission() == 0) {
                active_touch_addr = a;
                Serial.printf("[TOUCH] Auto-detected touch controller at 0x%02X\\n", a);
                break;
            }
        }
        if (active_touch_addr == 0x00) {
            if (i2c_mutex) xSemaphoreGive(i2c_mutex);
            static unsigned long last_err = 0;
            if (millis() - last_err > 3000) {
                last_err = millis();
                Serial.println("[TOUCH-ERR] Khong tim thay IC cam ung nao tren bus I2C!");
            }
            return false;
        }
    }

    if (active_touch_addr == 0x38) {
        Wire.beginTransmission(0x38);
        Wire.write(0x02); // Point to 0x02 (TD_STATUS) register
        uint8_t err = Wire.endTransmission();
        if (err != 0) {
            if (i2c_mutex) xSemaphoreGive(i2c_mutex);
            return false;
        }

        uint8_t n = Wire.requestFrom((uint16_t)0x38, (uint8_t)5);
        if (n < 5) {
            if (i2c_mutex) xSemaphoreGive(i2c_mutex);
            return false;
        }

        uint8_t points = Wire.read() & 0x0F; // 0x02: TD_STATUS
        uint8_t x_high = Wire.read();        // 0x03: Touch1 X_H & Event flag
        uint8_t x_low  = Wire.read();        // 0x04: Touch1 X_L
        uint8_t y_high = Wire.read();        // 0x05: Touch1 Y_H & Touch ID
        uint8_t y_low  = Wire.read();        // 0x06: Touch1 Y_L

        uint8_t event_flag = (x_high >> 6) & 0x03; // 00=Press Down, 01=Lift Up, 10=Contact, 11=No Event
        bool is_touched = (points >= 1 && points <= 2);

        if (is_touched) {
            int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
            int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;

            switch (global_touch_mode) {
                case 0: // Both inverted (chuan xac 100% ca 2 truc X va Y theo chieu xoay man hinh)
                    *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                    *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                    break;
                case 1: // Direct raw
                    *x = constrain(raw_x, 0, LCD_WIDTH - 1);
                    *y = constrain(raw_y, 0, LCD_HEIGHT - 1);
                    break;
                case 2: // Invert X
                    *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                    *y = constrain(raw_y, 0, LCD_HEIGHT - 1);
                    break;
                case 3: // Invert Y
                    *x = constrain(raw_x, 0, LCD_WIDTH - 1);
                    *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                    break;
                case 4: // Swapped axes (raw_x=Y, raw_y=X)
                    *x = constrain(raw_y, 0, LCD_WIDTH - 1);
                    *y = constrain(raw_x, 0, LCD_HEIGHT - 1);
                    break;
                case 5: // Swapped axes + Invert X
                    *x = constrain((LCD_WIDTH - 1) - raw_y, 0, LCD_WIDTH - 1);
                    *y = constrain(raw_x, 0, LCD_HEIGHT - 1);
                    break;
                case 6: // Swapped axes + Invert Y
                    *x = constrain(raw_y, 0, LCD_WIDTH - 1);
                    *y = constrain((LCD_HEIGHT - 1) - raw_x, 0, LCD_HEIGHT - 1);
                    break;
                case 7: // Swapped axes + Both inverted
                    *x = constrain((LCD_WIDTH - 1) - raw_y, 0, LCD_WIDTH - 1);
                    *y = constrain((LCD_HEIGHT - 1) - raw_x, 0, LCD_HEIGHT - 1);
                    break;
            }

            static unsigned long last_dbg = 0;
            if (millis() - last_dbg > 150) {
                last_dbg = millis();
                Serial.printf("[TOUCH] pts=%d evt=%d raw=(%d, %d) -> mapped=(%d, %d) [mode %d]\\n", 
                              points, event_flag, raw_x, raw_y, *x, *y, global_touch_mode);
            }
            if (i2c_mutex) xSemaphoreGive(i2c_mutex);
            return true;
        }
    } else if (active_touch_addr == 0x15) {
        Wire.beginTransmission(0x15);
        Wire.write(0x00);
        if (Wire.endTransmission() == 0 && Wire.requestFrom((int)0x15, 7) == 7) {
            Wire.read(); // reg 0x00
            Wire.read(); // reg 0x01
            uint8_t points = Wire.read() & 0x0F; // reg 0x02
            uint8_t x_high = Wire.read(); // reg 0x03
            uint8_t x_low  = Wire.read(); // reg 0x04
            uint8_t y_high = Wire.read(); // reg 0x05
            uint8_t y_low  = Wire.read(); // reg 0x06
            if (points > 0) {
                int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
                int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;
                *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                *y = constrain(raw_y, 0, LCD_HEIGHT - 1);
                if (i2c_mutex) xSemaphoreGive(i2c_mutex);
                return true;
            }
        }
    }
    if (i2c_mutex) xSemaphoreGive(i2c_mutex);
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
    } else {
        data->state = LV_INDEV_STATE_REL;
        data->point.x = last_touch_x;
        data->point.y = last_touch_y;
        if (was_pressed) {
            was_pressed = false;
            Serial.printf("[TOUCH] Released at (%d, %d)\\n", last_touch_x, last_touch_y);
        }
    }
}

// -----------------------------------------------------------------------------
"""

text = text[:start1] + new_touch_block + text[end1 + len('// -----------------------------------------------------------------------------'):]

old_setup = """    // 1. Hardware Reset Touch Chip
    pinMode(TOUCH_RST_PIN, OUTPUT);
    digitalWrite(TOUCH_RST_PIN, LOW);
    delay(20);
    digitalWrite(TOUCH_RST_PIN, HIGH);
    delay(50);
    pinMode(TOUCH_INT_PIN, INPUT_PULLUP);

    Wire.begin(I2C_PORT_SDA_PIN, I2C_PORT_SCL_PIN, I2C_BUS_FREQ_HZ);
    Wire.setTimeOut(30); // Phong chong I2C hang/deadlock tren bus cam ung FT6336
    scan_i2c_bus();"""

new_setup = """    // 1. Hardware Reset Touch Chip
    pinMode(TOUCH_RST_PIN, OUTPUT);
    digitalWrite(TOUCH_RST_PIN, LOW);
    delay(20);
    digitalWrite(TOUCH_RST_PIN, HIGH);
    delay(300); // Cho 300ms de FT6336 hoan tat self-calib sau Reset
    pinMode(TOUCH_INT_PIN, INPUT_PULLUP);

    Wire.begin(I2C_PORT_SDA_PIN, I2C_PORT_SCL_PIN, I2C_BUS_FREQ_HZ);
    Wire.setTimeOut(30); // Phong chong I2C hang/deadlock tren bus cam ung FT6336
    scan_i2c_bus();

    // Khoi tao che do hoat dong Normal & Polling cho FT6336
    if (active_touch_addr == 0x38) {
        Wire.beginTransmission(0x38);
        Wire.write(0x00); // DEV_MODE register
        Wire.write(0x00); // 0x00 = Normal operating mode
        Wire.endTransmission();

        Wire.beginTransmission(0x38);
        Wire.write(0xA4); // G_MODE register (Interrupt Mode)
        Wire.write(0x00); // 0x00 = Polling mode (cap nhat toa do lien tuc)
        Wire.endTransmission();
        Serial.println("[TOUCH] FT6336 da khoi tao thanh cong (DEV_MODE=Normal, G_MODE=Polling)");
    }"""

assert old_setup in text, "old_setup not found!"
text = text.replace(old_setup, new_setup, 1)

with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated main.cpp successfully!")
