#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - ES8311 LOW-POWER AUDIO CODEC DRIVER
 * Official Hardware Driver for ES3C28P Board (LCDWiki 2.8" ESP32-S3)
 * - ES8311 I2C Address: 0x18
 * - MCLK: GPIO 4 (256 * Fs = 4.096 MHz)
 * - BCLK: GPIO 5, LRCK: GPIO 7
 * - DOUT (Speaker DAC): GPIO 8
 * - DIN  (Microphone ADC): GPIO 6
 * - PA_EN (FM8002E Audio Amp): GPIO 1 (LOW = Enable, HIGH = Mute)
 * ==============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <driver/i2s.h>
#include <esp_rom_gpio.h>
#include <soc/gpio_sig_map.h>
#include "pins_config.h"

extern SemaphoreHandle_t i2c_mutex;

class ES8311AudioEngine {
private:
    uint8_t current_mic_gain = 5;

    bool write_reg(uint8_t reg, uint8_t val) {
        if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(20)) != pdTRUE) return false;
        Wire.beginTransmission(I2C_ADDR_ES8311);
        Wire.write(reg);
        Wire.write(val);
        bool res = (Wire.endTransmission() == 0);
        if (i2c_mutex) xSemaphoreGive(i2c_mutex);
        return res;
    }

    uint8_t read_reg(uint8_t reg) {
        if (i2c_mutex && xSemaphoreTake(i2c_mutex, pdMS_TO_TICKS(20)) != pdTRUE) return 0;
        Wire.beginTransmission(I2C_ADDR_ES8311);
        Wire.write(reg);
        Wire.endTransmission(false);
        Wire.requestFrom((uint16_t)I2C_ADDR_ES8311, (uint8_t)1, true);
        uint8_t res = Wire.available() ? Wire.read() : 0;
        if (i2c_mutex) xSemaphoreGive(i2c_mutex);
        return res;
    }

public:
    bool begin() {
        Serial.println("[AUDIO] Initializing ES8311 Codec on ES3C28P...");

        // 1. Cấu hình chân PA_EN (SC8002B Audio Amplifier: LOW = Enable, HIGH = Mute)
        pinMode(PA_EN_PIN, OUTPUT);
        digitalWrite(PA_EN_PIN, HIGH); // Mute lúc khởi động chống pop noise

        // 2. Kiểm tra kết nối I2C với ES8311
        Wire.beginTransmission(I2C_ADDR_ES8311);
        if (Wire.endTransmission() != 0) {
            Serial.println("[ERR] Khong tim thay ES8311 tren bus I2C (0x18)!");
            return false;
        }

        // 3. Khởi tạo I2S peripheral TRƯỚC để cấp xung Master Clock (MCLK GPIO 4) cho ES8311
        init_esp32_i2s();
        delay(20);

        // 4. Trình tự khởi động chip ES8311 chuẩn Espressif & LCDWiki:
        write_reg(0x00, 0x1F); // Reset toàn bộ logic
        delay(20);
        write_reg(0x00, 0x00); // Release reset
        write_reg(0x00, 0x80); // Power on slave mode

        // Clock manager: Slave mode, 256*Fs
        // 0x3F: BẬT TOÀN BỘ xung nhịp DAC (CLKDAC_ON = bit 2) và ADC (CLKADC_ON = bit 3)!
        // (Nếu để 0x30 như trước, bit 2 = 0 làm khối DAC hoàn toàn bị ngắt clock và câm tiếng)
        write_reg(0x01, 0x3F); 
        write_reg(0x02, 0x00); // dig_mclk pre-divider/multiplier (1x)
        write_reg(0x03, 0x10); // ADC OSR = 64*Fs
        write_reg(0x04, 0x20); // DAC OSR = 128*Fs (Chuẩn 16kHz coeff_div Espressif)
        write_reg(0x05, 0x00); // ADC & DAC clock dividers = 1
        write_reg(0x06, 0x03); // BCLK divider = 4 (32 bits per frame)
        write_reg(0x07, 0x00); // LRCK normal polarity
        write_reg(0x08, 0xFF); // LRCK divider (256 BCLKs)

        // 5. Định dạng dữ liệu nối tiếp I2S: 16-bit Standard I2S
        write_reg(0x09, 0x0C); // DAC format: 16-bit Standard I2S
        write_reg(0x0A, 0x0C); // ADC format: 16-bit Standard I2S

        // 6. Cấp nguồn toàn diện các khối tương tự, Bias, Charge Pump & DAC Reference (CHUẨN ESP-ADF):
        write_reg(0x0D, 0x01); // Analog section start
        write_reg(0x0E, 0x02); // Enable Analog PGA & ADC Modulator
        write_reg(0x10, 0x1F); // BẮT BUỘC: Power-up ADC & DAC bias circuit & references!
        write_reg(0x11, 0x7F); // BẮT BUỘC: Power-up DAC Vref and charge pump!
        write_reg(0x12, 0x00); // DAC Power ON (PDN_DAC = 0)
        write_reg(0x13, 0x10); // DAC Output Routing / HP-Drive Power ON!
        write_reg(0x14, 0x1A); // Enable ADC & Mic Bias (+30dB analog PGA gain)
        write_reg(0x15, 0x40); // ADC ramp
        write_reg(0x16, 0x07); // ADC Scale (+42dB max gain)
        write_reg(0x17, 0xDF); // ADC digital volume 0xDF = +16dB High-Sensitivity Gain cho Electret Mic
        write_reg(0x1B, 0x0A); // ADC High pass filter
        write_reg(0x1C, 0x6A); // ADC EQ
        write_reg(0x37, 0x48); // DAC EQ Bypass
        write_reg(0x44, 0x58); // Internal reference signal (ADCL + DACR)
        write_reg(0x45, 0x00); // GP control

        // 7. Mở DAC & Thiết lập âm lượng mặc định
        write_reg(0x31, 0x00); // Unmute DAC
        set_speaker_volume(90);
        set_mic_gain(current_mic_gain);

        Serial.println("[AUDIO] ES8311 Audio Codec ready & I2S MCLK (GPIO 4) Active!");
        return true;
    }

    void dump_registers() {
        Serial.println("=== ES8311 REGISTERS DUMP ===");
        for (uint8_t r = 0; r <= 0x45; r++) {
            uint8_t v = read_reg(r);
            Serial.printf("Reg 0x%02X = 0x%02X\n", r, v);
        }
    }

    void set_speaker_volume(uint8_t vol_percent) {
        if (vol_percent > 100) vol_percent = 100;
        // Chuẩn ES8311 Register 0x32 (DAC_VOLUME):
        // 0x00 = -95.5dB (Mute)
        // 0xBF = 0.0dB (Chuẩn Unity Gain)
        // 0xD8 = +12.0dB (Đảm bảo âm lượng loa to, rõ nét khi qua amply SC8002B)
        uint8_t reg32 = 0x00;
        if (vol_percent > 0) {
            reg32 = (uint8_t)map(vol_percent, 1, 100, 0x80, 0xD8);
        }
        write_reg(0x32, reg32);
    }

    void set_mic_gain(uint8_t gain) {
        if (gain < 1) gain = 1;
        if (gain > 7) gain = 7;
        current_mic_gain = gain;

        // Chuẩn chính thức ESP-ADF & Espressif es8311.c:
        // - Reg 0x14: 0x1A (+30dB Analog PGA)
        // - Reg 0x16: gain 1..7 tương ứng mức tăng Scale từ +6dB đến +42dB (bước 6dB)
        // - Reg 0x17: 0xDF (+16.0dB Digital Volume Boost cho Electret Mic độ nhạy cao)
        write_reg(0x0E, 0x02); // Đảm bảo PGA & ADC Modulator luôn được cấp nguồn
        write_reg(0x14, 0x1A);
        write_reg(0x16, gain);
        write_reg(0x17, 0xDF);
        Serial.printf("[AUDIO] ES8311 Mic Gain Cap %d: PGA=0x1A, Scale=0x%02X (+%ddB), Reg0x17=0xDF (+16dB)\n",
                      gain, gain, gain * 6);
    }

    uint8_t get_mic_gain() const {
        return current_mic_gain;
    }

    bool enable_mic(bool enable) {
        if (enable) {
            set_mic_gain(current_mic_gain);
            return true;
        } else {
            return write_reg(0x14, 0x00);
        }
    }

    void mute_speaker(bool mute) {
        // SC8002B Audio Amp: LOW = Enable, HIGH = Shutdown/Mute
        digitalWrite(PA_EN_PIN, mute ? HIGH : LOW);
        write_reg(0x31, 0x00); // Luôn giữ DAC unmute, việc ngắt tiếng do PA_EN đảm nhiệm
    }

    // Phát âm thanh kiểm tra (Tone Beep) trực tiếp qua I2S DMA Stereo
    void play_beep(uint16_t freq_hz = 1000, uint16_t duration_ms = 700) {
        write_reg(0x31, 0x00); // Unmute DAC
        write_reg(0x32, 0xBF); // Mức âm lượng chuẩn 0dB, trong trẻo sạch tiếng
        mute_speaker(false);   // Kéo PA_EN = LOW mở IC khuếch đại SC8002B
        delay(40);

        const size_t buf_samples = 256;
        int16_t sample_buffer[buf_samples * 2]; // Stereo Interleaved L + R
        float step = (float)freq_hz / (float)AUDIO_SAMPLE_RATE;
        for (size_t i = 0; i < buf_samples; i++) {
            float angle = 2.0f * 3.14159265f * (float)i * step;
            int16_t val = (int16_t)(sin(angle) * 20000.0f);
            sample_buffer[2 * i]     = val; // Kênh Trái
            sample_buffer[2 * i + 1] = val; // Kênh Phải
        }

        size_t samples_total = (AUDIO_SAMPLE_RATE * duration_ms) / 1000;
        size_t loops = samples_total / buf_samples;
        if (loops == 0) loops = 1;
        size_t bytes_written = 0;

        for (size_t c = 0; c < loops; c++) {
            i2s_write(I2S_NUM_0, sample_buffer, sizeof(sample_buffer), &bytes_written, portMAX_DELAY);
        }

        delay(30);
    }

    // Phát một nốt âm thanh chuẩn tần số qua I2S DMA Stereo
    void play_tone(uint16_t freq_hz, uint16_t duration_ms, float volume = 1.0f) {
        const size_t buf_samples = 256;
        int16_t sample_buffer[buf_samples * 2]; // Stereo Interleaved L + R
        float step = (float)freq_hz / (float)AUDIO_SAMPLE_RATE;
        float amp = 26000.0f * constrain(volume, 0.0f, 1.0f);
        for (size_t i = 0; i < buf_samples; i++) {
            float angle = 2.0f * 3.14159265f * (float)i * step;
            int16_t val = (int16_t)(sin(angle) * amp);
            sample_buffer[2 * i]     = val;
            sample_buffer[2 * i + 1] = val;
        }

        size_t samples_total = (AUDIO_SAMPLE_RATE * duration_ms) / 1000;
        size_t loops = samples_total / buf_samples;
        if (loops == 0) loops = 1;

        size_t bytes_written = 0;
        for (size_t c = 0; c < loops; c++) {
            i2s_write(I2S_NUM_0, sample_buffer, sizeof(sample_buffer), &bytes_written, portMAX_DELAY);
        }
    }

    // Phát giai điệu chuông đàm thoại du dương (Ding-Dong 2 hồi to rõ)
    void play_ringtone() {
        write_reg(0x31, 0x00); // Unmute DAC
        write_reg(0x32, 0xC8); // Mức âm lượng chuông to rõ (+4.5dB)
        mute_speaker(false);   // Mở amply SC8002B
        delay(40);
        // Hồi 1: E5 (659Hz) -> A5 (880Hz)
        play_tone(659, 120, 0.85f);
        delay(25);
        play_tone(880, 200, 0.9f);
        delay(80);
        // Hồi 2: E5 (659Hz) -> A5 (880Hz)
        play_tone(659, 120, 0.85f);
        delay(25);
        play_tone(880, 250, 0.9f);
        delay(40);
    }

private:
    void init_esp32_i2s() {
        // Cấu hình Duplex I2S Master trên ESP32-S3 (Stereo 16-bit 16kHz kèm MCLK GPIO 4)
        i2s_config_t i2s_config = {
            .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX),
            .sample_rate = AUDIO_SAMPLE_RATE,
            .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
            .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // Stereo Interleaved chuẩn ES8311
            .communication_format = I2S_COMM_FORMAT_STAND_I2S,
            .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
            .dma_buf_count = 8,
            .dma_buf_len = 256,
            .use_apll = false,
            .tx_desc_auto_clear = true,
            .fixed_mclk = AUDIO_SAMPLE_RATE * 256 // 4.096 MHz Master Clock
        };

        i2s_pin_config_t pin_config = {
            .mck_io_num = I2S_MCLK_PIN,     // GPIO 4 (Bắt buộc cho ES3C28P)
            .bck_io_num = I2S_BCLK_PIN,     // GPIO 5 (Bit Clock)
            .ws_io_num = I2S_LRCK_PIN,       // GPIO 7 (L/R Word Select)
            .data_out_num = I2S_DOUT_PIN,    // GPIO 8
            .data_in_num = I2S_DIN_PIN       // GPIO 6
        };

        i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
        i2s_set_pin(I2S_NUM_0, &pin_config);

        // DUAL-ROUTING DOUT: Xuất dữ liệu I2S DOUT đồng thời ra CẢ GPIO 8 VÀ GPIO 6 qua GPIO Matrix!
        // Đảm bảo dù phần cứng cắm DOUT ở chân 8 hay chân 6 thì âm thanh DAC đều nhận được 100%!
        esp_rom_gpio_connect_out_signal(8, I2S0O_SD_OUT_IDX, false, false);
        esp_rom_gpio_connect_out_signal(6, I2S0O_SD_OUT_IDX, false, false);

        i2s_zero_dma_buffer(I2S_NUM_0);
    }
};

extern ES8311AudioEngine audioEngine;
