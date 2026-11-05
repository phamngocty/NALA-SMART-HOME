#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - ES3C28P OFFICIAL PIN CONFIGURATION
 * Board: LCDWiki ES3C28P (2.8" ESP32-S3 240x320 Capacitive Touch IPS)
 * Verified against official LCDWiki ES3C28P schematic & datasheet
 * ==============================================================================
 */

#include <Arduino.h>

// -----------------------------------------------------------------------------
// 1. I2C SHARED BUS (CAPACITIVE TOUCH FT6336G & AUDIO CODEC ES8311)
// -----------------------------------------------------------------------------
#define I2C_PORT_SCL_PIN        15      // SCL (in rõ trên FPC & PCB)
#define I2C_PORT_SDA_PIN        16      // SDA (in rõ trên FPC & PCB)
#define I2C_BUS_FREQ_HZ         100000  // 100kHz Standard Mode for rock-solid FT6336 + ES8311

// Capacitive Touch & Audio Codec I2C Addresses
#define TOUCH_RST_PIN           18      // Active LOW Reset
#define TOUCH_INT_PIN           17      // Interrupt pin
#define I2C_ADDR_FT6336U        0x38    // Dia chi I2C cua FT6336G
#define I2C_ADDR_CST816S        0x15    // CST816S
#define I2C_ADDR_GT911          0x5D    // GT911
#define I2C_ADDR_ES8311         0x18    // Dia chi I2C cua IC ES8311

// -----------------------------------------------------------------------------
// 2. MÀN HÌNH 2.8" LCD (ILI9341V 240x320 SPI)
// -----------------------------------------------------------------------------
#define LCD_WIDTH               240
#define LCD_HEIGHT              320

#define LCD_SPI_HOST            SPI2_HOST
#define LCD_SPI_MOSI_PIN        11      // TFT_MOSI
#define LCD_SPI_MISO_PIN        13      // TFT_MISO
#define LCD_SPI_SCLK_PIN        12      // TFT_SCK
#define LCD_SPI_CS_PIN          10      // TFT_CS
#define LCD_SPI_DC_PIN          46      // TFT_DC / RS
#define LCD_SPI_RST_PIN         -1      // Reset noi EN

// Đèn nền LCD (Backlight - GPIO 45 chính, HIGH = ON)
#define LCD_BL_PIN              45
#define LCD_BL_ALT_PIN          21      // Chân mở rộng phụ
#define LCD_BL_PWM_CHANNEL      0
#define LCD_BL_PWM_FREQ         5000
#define LCD_BL_PWM_RES          8

// -----------------------------------------------------------------------------
// 3. RGB LED TÍCH HỢP MẶT SAU (WS2812 / NeoPixel)
// -----------------------------------------------------------------------------
#define RGB_LED_PIN             42      // Chân dieu khien LED RGB SMD mat sau
#define RGB_LED_COUNT           1

// -----------------------------------------------------------------------------
// 4. KHE THẺ NHỚ MICRO SD (SDIO 4-BIT)
// -----------------------------------------------------------------------------
#define SD_CLK_PIN              38
#define SD_CMD_PIN              40
#define SD_D0_PIN               39
#define SD_D1_PIN               41
#define SD_D2_PIN               48
#define SD_D3_PIN               47

// -----------------------------------------------------------------------------
// 5. ÂM THANH I2S & ES8311 CODEC (MIC TÍCH HỢP & LOA SPEAKER PORT)
// -----------------------------------------------------------------------------
#define AUDIO_SAMPLE_RATE       16000
#define AUDIO_BITS_PER_SAMPLE   16

#define I2S_MCLK_PIN            4       // Audio I2S Master Clock
#define I2S_BCLK_PIN            5       // Audio I2S Bit Clock
#define I2S_LRCK_PIN            7       // Audio I2S Word Select (WS)
#define I2S_DOUT_PIN            6       // Audio Data Out (ESP32 -> Codec DAC)
#define I2S_DIN_PIN             8       // Audio Data In (Mic ADC -> ESP32)
#define PA_EN_PIN               1       // Power Amp Enable (LOW = Bật loa FM8002E)

// -----------------------------------------------------------------------------
// 6. NÚT NHẤN VẬT LÝ & EXPAND PINS
// -----------------------------------------------------------------------------
#define BUTTON_BOOT_PIN         0       // Nút BOOT vật lý trên PCB (Active LOW)
#define EXPAND_PIN_IO2          2
#define EXPAND_PIN_IO3          3
#define EXPAND_PIN_IO14         14
#define EXPAND_PIN_IO21         21
