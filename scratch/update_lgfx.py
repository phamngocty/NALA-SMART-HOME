import os

path = r'firmware_esp32s3_panel\src\main.cpp'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read().replace('\r\n', '\n')

old_class = '''class LGFX_Panel : public lgfx::LGFX_Device {
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

new_class = '''class LGFX_Panel : public lgfx::LGFX_Device {
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

assert old_class in c, "old_class not found in main.cpp!"
c = c.replace(old_class, new_class, 1)

old_read_touch = '''// Đọc tọa độ cảm ứng điện dung FT6336G / CST816S đảo 180° chuẩn xác
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
        uint8_t points = ft_read_reg_byte(0x02) & 0x0F;
        if (points >= 1 && points <= 2) {
            uint8_t x_high = ft_read_reg_byte(0x03);
            uint8_t x_low  = ft_read_reg_byte(0x04);
            uint8_t y_high = ft_read_reg_byte(0x05);
            uint8_t y_low  = ft_read_reg_byte(0x06);
            uint8_t event_flag = (x_high >> 6) & 0x03;
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
}'''

new_read_touch = '''// Đọc tọa độ cảm ứng kết hợp LovyanGFX chuẩn + Fallback INT Pin
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

assert old_read_touch in c, "old_read_touch not found in main.cpp!"
c = c.replace(old_read_touch, new_read_touch, 1)

c = c.replace('#define CURRENT_FIRMWARE_VERSION "v3.1.1"', '#define CURRENT_FIRMWARE_VERSION "v3.1.2"')

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(c)

print("Successfully applied both LGFX Touch driver and INT Fallback!")
