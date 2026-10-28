#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - ES8311 LOW-POWER AUDIO CODEC DRIVER
 * Initializes I2C registers of ES8311 on ES3C28P Board (Address 0x18)
 * Configures ADC (Microphone) and DAC (Speaker Port) + PA_EN (GPIO 1)
 * ==============================================================================
 */

#include <Arduino.h>
#include <Wire.h>
#include <driver/i2s.h>
#include "pins_config.h"

class ES8311AudioEngine {
private:
    bool write_reg(uint8_t reg, uint8_t val) {
        Wire.beginTransmission(I2C_ADDR_ES8311);
        Wire.write(reg);
        Wire.write(val);
        return (Wire.endTransmission() == 0);
    }

public:
    bool begin() {
        Serial.println("[AUDIO] Initializing ES8311 Codec over I2C (0x18)...");

        // Bật chân kích hoạt mạch khuếch đại loa FM8002E (PA_EN - Active LOW)
        pinMode(PA_EN_PIN, OUTPUT);
        digitalWrite(PA_EN_PIN, HIGH); // Mute lúc khởi động để chống nổ loa (POP noise)

        // Reset ES8311
        write_reg(0x00, 0x1F); // Reset all registers
        delay(20);
        write_reg(0x00, 0x00); // Normal operation

        // Clock manager: Slave mode, 256*Fs
        write_reg(0x01, 0x30);
        write_reg(0x02, 0x10);
        write_reg(0x03, 0x10);
        write_reg(0x04, 0x10);
        write_reg(0x05, 0x00);

        // System Power Up
        write_reg(0x0D, 0x01); // Power up analog circuit
        write_reg(0x0E, 0xBF);
        write_reg(0x12, 0x00); // Enable DAC
        write_reg(0x14, 0x1A); // Enable ADC

        // I2S Serial Data Format: 16-bit Standard I2S
        write_reg(0x09, 0x0C); // I2S standard format, 16-bit
        write_reg(0x0A, 0x0C); // I2S standard format, 16-bit

        // Set Default Volumes
        set_speaker_volume(80);
        set_mic_gain(18);

        // Khởi tạo giao tiếp I2S trên ESP32-S3
        init_esp32_i2s();

        Serial.println("[AUDIO] ES8311 Audio Codec ready!");
        return true;
    }

    void set_speaker_volume(uint8_t vol_percent) {
        // ES8311 DAC Volume Register 0x32 (0x00 = +0dB, 0xFF = -95.5dB)
        uint8_t reg_val = map(constrain(vol_percent, 0, 100), 0, 100, 0xBF, 0x00);
        write_reg(0x32, reg_val);
    }

    void set_mic_gain(uint8_t gain_db) {
        // ES8311 ADC Gain Register 0x16 (PGA gain: 0..30dB)
        uint8_t reg_val = constrain(gain_db / 3, 0, 10);
        write_reg(0x16, (reg_val << 4) | reg_val);
    }

    void mute_speaker(bool mute) {
        digitalWrite(PA_EN_PIN, mute ? HIGH : LOW);
    }

private:
    void init_esp32_i2s() {
        // Cấu hình Duplex I2S hoặc Half-Duplex trên ESP32-S3
        i2s_config_t i2s_config = {
            .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX | I2S_MODE_RX),
            .sample_rate = AUDIO_SAMPLE_RATE,
            .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
            .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
            .communication_format = I2S_COMM_FORMAT_STAND_I2S,
            .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
            .dma_buf_count = 8,
            .dma_buf_len = 256,
            .use_apll = false,
            .tx_desc_auto_clear = true,
            .fixed_mclk = 0
        };

        i2s_pin_config_t pin_config = {
            .bck_io_num = I2S_BCLK_PIN,     // GPIO 5
            .ws_io_num = I2S_LRCK_PIN,       // GPIO 7
            .data_out_num = I2S_DOUT_PIN,    // GPIO 6 (Speaker)
            .data_in_num = I2S_DIN_PIN       // GPIO 8 (Mic)
        };

        i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
        i2s_set_pin(I2S_NUM_0, &pin_config);
        i2s_zero_dma_buffer(I2S_NUM_0);
    }
};

extern ES8311AudioEngine audioEngine;
