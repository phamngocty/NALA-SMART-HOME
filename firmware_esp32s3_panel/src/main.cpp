/**
 * ==============================================================================
 * NALA SMART HOME - PHASE 2 & 3: LVGL 8.3.11 WALL PANEL & AI INTERCOM
 * 1. Màn hình Dark Modern Glassmorphism chuẩn LVGL 8.3.11 trên Core 1
 * 2. Cảm ứng điện dung FT6336G đảo 180° chuẩn xác không lệch điểm chạm
 * 3. Tự phát AP "NALA-PANEL-[MÃ]" & Web 192.168.4.1 khi chưa cấu hình WiFi
 * 4. WebSocket 2 chiều với NAS Hub, tự đồng bộ tên phòng & thực thể Home Assistant
 * 5. Push-to-Talk (PTT) Mic ES8311 DMA Half-Duplex -> Faster-Whisper GPU -> Piper TTS
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <Wire.h>
#include <SPI.h>
#include <Adafruit_NeoPixel.h>

#define LGFX_USE_V1
#include <LovyanGFX.hpp>
#include <lvgl.h>

#include "pins_config.h"
#include "protocol_defs.h"
#include "state_machine.h"
#include "nvs_config_store.h"
#include "audio_es8311_engine.h"
#include "ws_client_manager.h"
#include "wifi_captive_portal.h"
#include "ui_lvgl_dashboard.h"
#include "FontMaker.h"
#include "radar_ld2410_engine.h"

// -----------------------------------------------------------------------------
// 1. LGFX HARDWARE DISPLAY DRIVER (ILI9341V SPI 40MHz)
// -----------------------------------------------------------------------------
class LGFX_Panel : public lgfx::LGFX_Device {
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
};

static LGFX_Panel tft;
static Adafruit_NeoPixel rgb_led(RGB_LED_COUNT, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);

// Bộ dựng Font Tiếng Việt UTF-8 có dấu (FontMaker)
static void setpx_font(int16_t x, int16_t y, uint16_t color) {
    tft.drawPixel(x, y, color);
}
static MakeFont fontMaker(&setpx_font);

NVSConfigStore nvsStore;
ES8311AudioEngine audioEngine;
WSClientManager wsManager;
WiFiCaptivePortal captivePortal;
UILVGLDashboard uiDashboard;
RadarLD2410Engine radarEngine;
SemaphoreHandle_t lvgl_mutex = NULL;
SemaphoreHandle_t i2c_mutex = NULL;

#include "ota_manager.h"
#include "esp_ota_ops.h"
#include <ESP32Time.h>
ESP32Time rtc(7 * 3600); // Múi giờ Việt Nam GMT+7 (offset 25200s)
volatile bool is_ota_running = false;
#define CURRENT_FIRMWARE_VERSION "v3.6.9"

// Trạng thái hệ thống
enum PanelState {
    PANEL_BOOTING,
    PANEL_AP_PROVISIONING,
    PANEL_CONNECTING_WIFI,
    PANEL_OPERATIONAL
};
static PanelState current_state = PANEL_BOOTING;

static String device_mac = "";
static String pairing_code = ""; // 4 ký tự cuối MAC

// Cờ PTT Audio
static volatile bool is_recording_ptt = false;

// Pre-Roll Ring Buffer cho Wake Word ranh tay (Luu 560ms am thanh truoc tieng noi trong 8MB PSRAM)
#define WAKE_PREROLL_FRAMES 35 // 35 khung * 16ms = 560ms
static int16_t (*wake_preroll_buf)[AUDIO_FRAME_SAMPLES] = nullptr;
static uint8_t wake_ring_head = 0;
static uint8_t wake_ring_count = 0;
static volatile uint8_t ptt_target_id = TARGET_ID_AI_SERVER;
static volatile bool ptt_start_flag = false;
static volatile uint8_t my_intercom_id = 0x01; // Dynamic Intercom ID from NAS Hub

// Cờ Cuộc Gọi Đàm Thoại Rảnh Tay Liên Phòng (Hands-Free Intercom Call V2)
static volatile bool is_intercom_call_active = false;
static volatile uint8_t intercom_peer_id = 0x00;
static char intercom_peer_name[48] = {0};

// Cờ phiên Đánh thức Rảnh tay (Hands-Free Wake Session)
static volatile bool is_hands_free_session = false;
static unsigned long hands_free_start_time = 0;
static unsigned long hands_free_last_voice = 0;

// Cờ phản hồi thức tỉnh kiểu Xiaozhi (Chờ phát xong câu nói "Dạ, em nghe!" rồi mới mở mic thu âm)
static volatile bool is_waiting_wake_speech = false;
static unsigned long wake_trigger_start_ms = 0;
static volatile unsigned long last_speaker_active_ms = 0; // Chống dội âm (Echo) loa vào Mic gây lặp Wake Word

// Cờ Trò Chuyện Liên Tục (Xiaozhi Continuous Listening & Timeout)
static volatile bool is_continuous_listening = false;
static unsigned long continuous_listen_start = 0;
static uint32_t continuous_listen_timeout_ms = 8000;

// Forward declarations
void notify_settings_changed();
void send_device_registration();

// Theo dõi nút BOOT cứng
static uint32_t boot_button_press_time = 0;
static bool boot_button_held = false;

// -----------------------------------------------------------------------------
// 2. LVGL 8.3.11 DOUBLE BUFFER & DRIVER CALLBACKS
// -----------------------------------------------------------------------------
static lv_disp_draw_buf_t draw_buf;
static lv_color_t* buf1 = nullptr;
static lv_color_t* buf2 = nullptr;
static lv_color_t buf_fallback[LCD_WIDTH * 20];
static lv_disp_drv_t disp_drv;
static lv_indev_drv_t indev_drv;

// Flush pixels từ bộ đệm LVGL ra màn hình qua LovyanGFX
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
    uint32_t w = (area->x2 - area->x1 + 1);
    uint32_t h = (area->y2 - area->y1 + 1);
    tft.startWrite();
    tft.setAddrWindow(area->x1, area->y1, w, h);
    tft.writePixels((lgfx::rgb565_t *)&color_p->full, w * h);
    tft.endWrite();
    lv_disp_flush_ready(disp);
}

static uint8_t active_touch_addr = 0x00;

void scan_i2c_bus() {
    Serial.println("[I2C] --- Bắt đầu quét bus I2C (SDA=16, SCL=15) ---");
    int count = 0;
    active_touch_addr = 0x00;
    for (uint8_t addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        uint8_t err = Wire.endTransmission();
        if (err == 0) {
            Serial.printf("[I2C] -> Tìm thấy thiết bị tại 0x%02X", addr);
            if (addr == 0x38) {
                Serial.print(" (FT6336U/FT6236 Touch)");
                if (active_touch_addr == 0x00) active_touch_addr = 0x38;
            } else if (addr == 0x15) {
                Serial.print(" (CST816S/CST816T Touch)");
                if (active_touch_addr == 0x00) active_touch_addr = 0x15;
            } else if (addr == 0x1A) {
                Serial.print(" (CST328 Touch)");
                if (active_touch_addr == 0x00) active_touch_addr = 0x1A;
            } else if (addr == 0x5D || addr == 0x14) {
                Serial.print(" (GT911 Touch)");
                if (active_touch_addr == 0x00) active_touch_addr = addr;
            } else if (addr == 0x18) {
                Serial.print(" (ES8311 Audio Codec)");
            }
            Serial.println();
            count++;
        }
    }
    Serial.printf("[I2C] --- Quét xong: %d thiết bị. Touch address: 0x%02X ---\n", count, active_touch_addr);
}

static uint8_t global_touch_mode = 0; // 0: Both Inverted (chuan 100%), 1: Direct raw, 2: Invert X, 3: Invert Y, 4-7: Swapped axes

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
    Serial.printf("[TOUCH-CALIB] Switched to mode %d: %s\n", global_touch_mode, mode_desc[global_touch_mode]);
}

// Đọc tọa độ cảm ứng điện dung FT6336 đảo 180° chuẩn xác - Single Burst Read 5 bytes
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

                switch (global_touch_mode) {
                    case 0: // Both inverted (Chuan LCDWiki ILI9341 180 deg)
                        *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                        *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                        break;
                    case 1: // Direct raw (Khong dao truc)
                        *x = constrain(raw_x, 0, LCD_WIDTH - 1);
                        *y = constrain(raw_y, 0, LCD_HEIGHT - 1);
                        break;
                    case 2: // Invert X only
                        *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
                        *y = constrain(raw_y, 0, LCD_HEIGHT - 1);
                        break;
                    case 3: // Invert Y only
                        *x = constrain(raw_x, 0, LCD_WIDTH - 1);
                        *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
                        break;
                    case 4: // Swapped axes (raw_y -> x, raw_x -> y)
                        *x = constrain(raw_y, 0, LCD_WIDTH - 1);
                        *y = constrain(raw_x, 0, LCD_HEIGHT - 1);
                        break;
                    case 5: // Swapped + Invert X
                        *x = constrain((LCD_WIDTH - 1) - raw_y, 0, LCD_WIDTH - 1);
                        *y = constrain(raw_x, 0, LCD_HEIGHT - 1);
                        break;
                    case 6: // Swapped + Invert Y
                        *x = constrain(raw_y, 0, LCD_WIDTH - 1);
                        *y = constrain((LCD_HEIGHT - 1) - raw_x, 0, LCD_HEIGHT - 1);
                        break;
                    case 7: // Swapped + Both inverted
                        *x = constrain((LCD_WIDTH - 1) - raw_y, 0, LCD_WIDTH - 1);
                        *y = constrain((LCD_HEIGHT - 1) - raw_x, 0, LCD_HEIGHT - 1);
                        break;
                }

                static unsigned long last_raw_log = 0;
                if (millis() - last_raw_log > 120) {
                    last_raw_log = millis();
                    Serial.printf("[TOUCH-RAW] raw=(%d, %d) -> mapped=(%d, %d) [mode %d]\n", raw_x, raw_y, *x, *y, global_touch_mode);
                }

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
        was_pressed = true;
        static unsigned long last_pr_log = 0;
        if (millis() - last_pr_log > 100) {
            last_pr_log = millis();
            Serial.printf("[LVGL-INDEV] PRESSED at (%d, %d)\n", x, y);
        }
    } else {
        data->state = LV_INDEV_STATE_REL;
        data->point.x = last_touch_x;
        data->point.y = last_touch_y;
        if (was_pressed) {
            was_pressed = false;
            Serial.printf("[LVGL-INDEV] RELEASED at (%d, %d)\n", last_touch_x, last_touch_y);
        }
    }
}

// -----------------------------------------------------------------------------
// 3. UI ACTION CALLBACKS
// -----------------------------------------------------------------------------
static unsigned long ws_ping_start_ms = 0;

void run_speaker_test() {
    Serial.println("[DIAG] Bắt đầu test Loa (ES3C28P Hardware)...");
    uiDashboard.set_diag_result("Loa: Đang phát thử âm thanh...", 0x38BDF8);
    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255));
    rgb_led.show();

    audioEngine.mute_speaker(false);
    audioEngine.set_speaker_volume(95);

    // 1. Tone 1000Hz (0.5s)
    audioEngine.play_tone(1000, 500, 0.95f);
    delay(80);

    // 2. Chuông đàm thoại Ding-Dong du dương
    audioEngine.play_ringtone();

    // Mute loa sau khi test xong
    audioEngine.mute_speaker(true);

    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
    rgb_led.show();
    uiDashboard.set_diag_result("Loa: Kiểm tra hoàn tất!", 0x10B981);
    Serial.println("[DIAG] Hoàn tất test loa!");
}

void run_mic_test() {
    static bool is_testing = false;
    if (is_testing) return;
    is_testing = true;

    Serial.println("[DIAG] Test Mic phong cách Discord (Thu 1.2s -> Phát lại delay 1s)...");
    uiDashboard.set_diag_result("Mic: Đang thu... (Hãy nói)", 0x3B82F6);
    lv_refr_now(NULL);
    rgb_led.setPixelColor(0, rgb_led.Color(255, 120, 0)); // Vàng cam đang thu
    rgb_led.show();

    // 1. Tiếng bíp rất ngắn (40ms) báo hiệu bắt đầu nói
    audioEngine.play_beep(1200, 40);
    delay(80); // Chờ DMA xả hết âm thanh tiếng bíp ra ngoài loa

    // Mute loa trong lúc thu âm để chống feedback/hú
    audioEngine.mute_speaker(true);
    audioEngine.enable_mic(true);
    audioEngine.set_mic_gain(nvsStore.get_mic_gain());

    // Flush bỏ toàn bộ các mẫu dơ/tiếng bíp còn sót lại trong DMA buffer
    size_t flush_bytes = 0;
    int16_t dummy[256 * 2];
    for (int k = 0; k < 6; k++) {
        i2s_read(I2S_NUM_0, dummy, sizeof(dummy), &flush_bytes, pdMS_TO_TICKS(20));
    }

    // Thu đúng 1.25 giây (20000 mẫu @ 16kHz = 40KB) - vừa vặn cho câu "Alo 1 2 3"
    const size_t total_mono_samples = 20000;
    int16_t* test_buf = (int16_t*)ps_malloc(total_mono_samples * sizeof(int16_t));
    if (!test_buf) {
        test_buf = (int16_t*)malloc(total_mono_samples * sizeof(int16_t));
    }
    if (!test_buf) {
        uiDashboard.set_diag_result("Mic: Lỗi cấp phát bộ nhớ!", 0xEF4444);
        is_testing = false;
        return;
    }

    int16_t stereo_chunk[256 * 2]; // 256 stereo pairs = 1024 bytes
    size_t recorded = 0;
    int64_t sum_sq_l = 0;
    int64_t sum_sq_r = 0;
    int16_t peak_val = 0;
    int zero_retries = 0;

    uint8_t gain_setting = nvsStore.get_mic_gain();
    int32_t sw_boost = (int32_t)(gain_setting * 2 + 6); // Cấp độ 1..7 -> 8x đến 20x khuếch đại số

    while (recorded < total_mono_samples) {
        size_t to_read_frames = min((size_t)256, total_mono_samples - recorded);
        size_t bytes_read = 0;
        i2s_read(I2S_NUM_0, stereo_chunk, to_read_frames * 2 * sizeof(int16_t), &bytes_read, pdMS_TO_TICKS(40));
        size_t frames_got = bytes_read / (2 * sizeof(int16_t));
        
        if (frames_got == 0) {
            zero_retries++;
            if (zero_retries > 10) break;
            delay(5);
            continue;
        }
        zero_retries = 0;

        for (size_t i = 0; i < frames_got; i++) {
            // ES8311 Mono ADC chuẩn phần cứng ES3C28P xuất dữ liệu trên kênh Trái (Left)
            int16_t sample_l = stereo_chunk[i * 2];
            int16_t sample_r = stereo_chunk[i * 2 + 1];
            sum_sq_r += ((int32_t)sample_r * sample_r);
            int16_t raw_sample = (abs((int)sample_l) >= abs((int)sample_r)) ? sample_l : sample_r;

            // Fade-in 50ms đầu (800 mẫu) triệt tiêu hoàn toàn xung điện áp lúc vừa bật mic
            size_t sample_idx = recorded + i;
            if (sample_idx < 800) {
                raw_sample = (int16_t)((int32_t)raw_sample * (int32_t)sample_idx / 800);
            }

            sum_sq_l += ((int32_t)sample_l * sample_l);

            // Khuếch đại kỹ thuật số giọng nói theo cài đặt NVS kèm soft limiter chống vỡ tiếng
            int32_t boosted = (int32_t)raw_sample * sw_boost;
            if (boosted > 28000) boosted = 28000;
            else if (boosted < -28000) boosted = -28000;

            test_buf[sample_idx] = (int16_t)boosted;
            if (abs((int)boosted) > peak_val) peak_val = abs((int)boosted);
        }
        recorded += frames_got;
    }

    int rms_l = (recorded > 0) ? (int)sqrt(sum_sq_l / recorded) : 0;
    int rms_r = (recorded > 0) ? (int)sqrt(sum_sq_r / recorded) : 0;
    int max_rms = max(rms_l, rms_r);
    Serial.printf("[DIAG] Mic thu %d mẫu | L_RMS=%d, R_RMS=%d, Boost=%dx, Peak=%d\n", recorded, rms_l, rms_r, sw_boost, peak_val);

    int64_t sum_dc = 0;
    for (size_t i = 0; i < recorded; i++) sum_dc += test_buf[i];
    int16_t avg_dc = recorded > 0 ? (int16_t)(sum_dc / recorded) : 0;
    Serial.printf("[DIAG] Sample dump: avg_dc=%d, first=[%d, %d, %d, %d], mid=[%d, %d, %d, %d]\n",
                  avg_dc, test_buf[0], test_buf[1], test_buf[2], test_buf[3],
                  test_buf[recorded/2], test_buf[recorded/2+1], test_buf[recorded/2+2], test_buf[recorded/2+3]);

    // 2. Chuyển ngay sang phát lại (Delay ~1s sau khi bắt đầu nói - chuẩn Discord Mic Test)
    uiDashboard.set_diag_result("Mic: Đang phát lại...", 0xF59E0B);
    lv_refr_now(NULL);
    rgb_led.setPixelColor(0, rgb_led.Color(0, 150, 255)); // Xanh dương đang phát
    rgb_led.show();

    // Mở amply và phát lại theo đúng mức âm lượng người dùng đã cài đặt
    audioEngine.mute_speaker(false);
    uint8_t play_vol = nvsStore.get().speaker_volume;
    if (play_vol < 80) play_vol = 95; // Đảm bảo âm lượng loa đủ lớn khi test
    audioEngine.set_speaker_volume(play_vol);
    Serial.printf("[DIAG] Phat lai loa voi am luong: %d%%\n", play_vol);
    delay(50);

    // Phát lại âm thanh giọng nói đã khuếch đại ra loa (Stereo L + R)
    size_t play_idx = 0;
    while (play_idx < recorded) {
        size_t chunk_s = min((size_t)256, recorded - play_idx);
        for (size_t i = 0; i < chunk_s; i++) {
            size_t curr_s = play_idx + i;
            int16_t s = test_buf[curr_s];
            // Fade-out 25ms cuối (400 mẫu) chống click khi amply tắt
            if (recorded > 400 && curr_s >= (recorded - 400)) {
                s = (int16_t)((int32_t)s * (int32_t)(recorded - curr_s) / 400);
            }
            stereo_chunk[i * 2]     = s;
            stereo_chunk[i * 2 + 1] = s;
        }
        size_t written = 0;
        i2s_write(I2S_NUM_0, stereo_chunk, chunk_s * 2 * sizeof(int16_t), &written, portMAX_DELAY);
        play_idx += chunk_s;
    }

    delay(350); // Chờ DMA xả hết âm thanh qua amply trước khi ngắt
    audioEngine.mute_speaker(true);
    free(test_buf);

    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá hoàn tất
    rgb_led.show();

    char res_str[64];
    if (max_rms > 30 || peak_val > 800) {
        snprintf(res_str, sizeof(res_str), "Mic: Tốt (Tín hiệu: %d)", peak_val);
        uiDashboard.set_diag_result(res_str, 0x10B981);
    } else {
        snprintf(res_str, sizeof(res_str), "Mic: Nhỏ (Tín hiệu: %d)", peak_val);
        uiDashboard.set_diag_result(res_str, 0xF59E0B);
    }
    lv_refr_now(NULL);
    is_testing = false;
    Serial.println("[DIAG] Test Mic hoàn thành!");
}

void check_ota_update_now() {
    Serial.println("[OTA] Đang kiểm tra cập nhật firmware từ NAS Hub...");
    if (WiFi.status() != WL_CONNECTED) {
        uiDashboard.set_diag_result("OTA: WiFi chưa kết nối!", 0xEF4444);
        return;
    }

    uiDashboard.set_diag_result("OTA: Đang kết nối NAS Hub...", 0x38BDF8);

    String ws_url = String(nvsStore.get().nas_ws_url);
    String http_base = "http://192.168.1.114:8765";
    int ws_idx = ws_url.indexOf("://");
    if (ws_idx >= 0) {
        int slash_idx = ws_url.indexOf('/', ws_idx + 3);
        if (slash_idx > 0) {
            http_base = "http://" + ws_url.substring(ws_idx + 3, slash_idx);
        } else {
            http_base = "http://" + ws_url.substring(ws_idx + 3);
        }
    }
    String url = http_base + "/api/ota/status";
    Serial.printf("[OTA] Status URL: %s\n", url.c_str());

    HTTPClient http;
    http.begin(url);
    http.setTimeout(5000);

    int httpCode = http.GET();
    if (httpCode == HTTP_CODE_OK) {
        String payload = http.getString();
        JsonDocument doc;
        DeserializationError err = deserializeJson(doc, payload);
        if (!err) {
            bool available = doc["available"] | false;
            String ver = doc["version"] | "";
            String download_url = doc["download_url"] | "";
            size_t size_bytes = doc["size_bytes"] | 0;

            if (available && download_url.length() > 0) {
                if (ver == CURRENT_FIRMWARE_VERSION) {
                    uiDashboard.set_diag_result(("Bản " + String(CURRENT_FIRMWARE_VERSION) + " đang mới nhất!").c_str(), 0x10B981);
                } else {
                    uiDashboard.set_diag_result(("Có bản mới " + ver + "! Đang nạp OTA...").c_str(), 0x34D399);
                    delay(500);
                    OTAManager::perform_ota(download_url, size_bytes, ver, pairing_code, &fontMaker, &tft, &wsManager);
                }
            } else {
                uiDashboard.set_diag_result("Chưa có firmware trên NAS Hub", 0xF59E0B);
            }
        } else {
            uiDashboard.set_diag_result("OTA: Lỗi phân tích JSON", 0xEF4444);
        }
    } else {
        uiDashboard.set_diag_result(("OTA: Lỗi HTTP " + String(httpCode)).c_str(), 0xEF4444);
    }
    http.end();
}

void run_ws_ping_test() {
    Serial.println("[DIAG] Bắt đầu ping WebSocket server...");
    uiDashboard.set_diag_result("Server: Đang ping NAS Hub...", 0xF59E0B);
    ws_ping_start_ms = millis();
    JsonDocument doc;
    doc["type"] = "ping";
    doc["client_time"] = ws_ping_start_ms;
    String out;
    serializeJson(doc, out);
    wsManager.send_text(out);
}

void on_ui_action(const char* target, const char* action, int value) {
    if (strcmp(target, "entity_toggle") == 0) {
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        String eid = String(action);
        String domain = "light";
        int dotIdx = eid.indexOf('.');
        if (dotIdx > 0) domain = eid.substring(0, dotIdx);
        doc["payload"]["domain"] = domain;
        doc["payload"]["service"] = "toggle";
        doc["payload"]["entity_id"] = eid;
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.printf("[HA] Gui toggle entity: %s (domain=%s)\n", action, domain.c_str());
    } else if (strcmp(target, "climate_temp") == 0) {
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "climate";
        doc["payload"]["service"] = "set_temperature";
        doc["payload"]["entity_id"] = action;
        doc["payload"]["service_data"]["temperature"] = (float)value / 10.0f;
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.printf("[HA] Climate set temp: %s -> %.1f\n", action, (float)value / 10.0f);
    } else if (strcmp(target, "climate_mode") == 0) {
        const char* modes[] = {"cool", "fan_only", "dry", "auto"};
        const char* m = (value >= 0 && value < 4) ? modes[value] : "cool";
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "climate";
        doc["payload"]["service"] = "set_hvac_mode";
        doc["payload"]["entity_id"] = action;
        doc["payload"]["service_data"]["hvac_mode"] = m;
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.printf("[HA] Climate set mode: %s -> %s\n", action, m);
    } else if (strcmp(target, "climate_fan") == 0) {
        const char* fan_modes[] = {"auto", "low", "medium", "high"};
        const char* fm = (value >= 0 && value < 4) ? fan_modes[value] : "auto";
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "climate";
        doc["payload"]["service"] = "set_fan_mode";
        doc["payload"]["entity_id"] = action;
        doc["payload"]["service_data"]["fan_mode"] = fm;
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.printf("[HA] Climate set fan mode: %s -> %s\n", action, fm);
    } else if (strcmp(target, "climate_swing") == 0) {
        const char* sm = (value == 1) ? "vertical" : "off";
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "climate";
        doc["payload"]["service"] = "set_swing_mode";
        doc["payload"]["entity_id"] = action;
        doc["payload"]["service_data"]["swing_mode"] = sm;
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.printf("[HA] Climate set swing mode: %s -> %s\n", action, sm);
    } else if (strcmp(target, "diag_speaker") == 0 || (strcmp(target, "diag") == 0 && strcmp(action, "speaker") == 0)) {
        run_speaker_test();
    } else if (strcmp(target, "diag_mic") == 0 || (strcmp(target, "diag") == 0 && strcmp(action, "mic") == 0)) {
        run_mic_test();
    } else if (strcmp(target, "diag_ws") == 0 || (strcmp(target, "diag") == 0 && strcmp(action, "ws_ping") == 0)) {
        run_ws_ping_test();
    } else if (strcmp(target, "check_update") == 0 || (strcmp(target, "system") == 0 && strcmp(action, "check_ota") == 0)) {
        check_ota_update_now();
    } else if (strcmp(target, "volume") == 0 || (strcmp(target, "settings") == 0 && strcmp(action, "vol") == 0)) {
        nvsStore.get().speaker_volume = value;
        audioEngine.set_speaker_volume(value);
        nvsStore.save_immediate();
        Serial.printf("[SETTINGS] Am luong da cap nhat: %d%%\n", value);
        notify_settings_changed();
    } else if (strcmp(target, "brightness") == 0 || (strcmp(target, "settings") == 0 && strcmp(action, "bright") == 0)) {
        nvsStore.get().lcd_brightness = value;
        tft.setBrightness(value);
        nvsStore.save_immediate();
        Serial.printf("[SETTINGS] Do sang da cap nhat: %d\n", value);
        notify_settings_changed();
    } else if (strcmp(target, "settings_mic") == 0 || (strcmp(target, "settings") == 0 && strcmp(action, "mic_gain") == 0)) {
        uint8_t gain = (uint8_t)constrain(value, 1, 7);
        nvsStore.set_mic_gain(gain);
        nvsStore.save_immediate(); // Lưu ngay lập tức vào Flash NVS
        audioEngine.set_mic_gain(gain);
        Serial.printf("[SETTINGS] Do nhay Mic da luu: %d (Cap do 1..7)\n", gain);
        notify_settings_changed();
    } else if (strcmp(target, "ring_on_call") == 0 || (strcmp(target, "settings") == 0 && strcmp(action, "ring_call") == 0)) {
        nvsStore.get().ring_on_call = (value == 1);
        nvsStore.save_immediate();
        Serial.printf("[SETTINGS] Ring on call set to: %s\n", nvsStore.get().ring_on_call ? "ON" : "OFF");
        if (nvsStore.get().ring_on_call) {
            audioEngine.play_ringtone(); // Đổ chuông thử nghiệm ngay khi người dùng BẬT chuông
            audioEngine.mute_speaker(true); // Ngắt amply sau khi phát xong chuông thử
        }
        notify_settings_changed();
    } else if (strcmp(target, "system") == 0 && strcmp(action, "enter_ap_mode") == 0) {
        Serial.println("[SYSTEM] Nguoi dung yeu cau vao Che Do Cau Hinh Soft-AP!");
        nvsStore.factory_reset();
        delay(250);
        ESP.restart();
    } else if (strcmp(target, "master_turn_off_all") == 0 || (strcmp(target, "ha_action") == 0 && strcmp(action, "master_turn_off_all") == 0)) {
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["action"] = "master_turn_off_all";
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.println("[HA] Gui lenh Master Turn Off All!");
    } else if (strcmp(target, "light") == 0) {
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "light";
        doc["payload"]["service"] = "toggle";
        doc["payload"]["entity_id"] = "light.phong_khach";
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.println("[HA] Gui toggle Den");
    } else if (strcmp(target, "fan") == 0) {
        JsonDocument doc;
        doc["type"] = "ha_action";
        doc["source"] = device_mac;
        doc["payload"]["domain"] = "fan";
        doc["payload"]["service"] = "toggle";
        doc["payload"]["entity_id"] = "fan.phong_khach";
        String out;
        serializeJson(doc, out);
        wsManager.send_text(out);
        Serial.println("[HA] Gui toggle Quat");
    } else if (strcmp(target, "ptt_ai") == 0) {
        if (strcmp(action, "start") == 0) {
            ptt_target_id = TARGET_ID_AI_SERVER; // 0x00
            ptt_start_flag = true;
            is_recording_ptt = true;
            audioEngine.stop_playback(); // Cắt lời tức thì (< 1ms) & xả sạch DMA buffer
            audioEngine.enable_mic(true);
            rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương
            rgb_led.show();
            // Gửi thông báo Abort lên WebSocket Server Hub để dừng ngay tác vụ TTS AI
            wsManager.send_text("{\"type\":\"abort\"}");
            Serial.println("[AI PTT] Start recording & send abort to server...");
        } else {
            is_recording_ptt = false;
            audioEngine.mute_speaker(false);
            rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá
            rgb_led.show();
            Serial.println("[AI PTT] Stop recording -> Sending END flag.");
        }
    } else if (strcmp(target, "ptt_intercom") == 0) {
        if (strcmp(action, "start") == 0) {
            ptt_target_id = (value == 0xFF || value <= 0) ? 0xFF : (uint8_t)value;
            ptt_start_flag = true;
            is_recording_ptt = true;
            audioEngine.mute_speaker(true);
            audioEngine.enable_mic(true);
            rgb_led.setPixelColor(0, rgb_led.Color(255, 0, 0)); // Đỏ đang đàm thoại
            rgb_led.show();
            Serial.printf("[INTERCOM PTT] Start call (From ID 0x%02X to Target 0x%02X)...\n", my_intercom_id, ptt_target_id);
        } else {
            is_recording_ptt = false;
            audioEngine.mute_speaker(false);
            rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
            rgb_led.show();
            Serial.println("[INTERCOM PTT] End call.");
        }
    } else if (strcmp(target, "intercom_hangup") == 0) {
        wsManager.send_text("{\"type\":\"intercom_hangup\"}");
        is_intercom_call_active = false;
        intercom_peer_id = 0x00;
        is_recording_ptt = false;
        audioEngine.mute_speaker(true);
        rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá
        rgb_led.show();
        audioEngine.play_wake_chime();
        bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
        if (taken) {
            uiDashboard.hide_incoming_call();
            uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
            xSemaphoreGive(lvgl_mutex);
        }
        Serial.println("[INTERCOM] Đã cúp máy từ nút bấm cảm ứng (Layer 2: Touch Hangup).");
    } else if (strcmp(target, "ai_model") == 0) {
        strncpy(nvsStore.get().ai_model, action, sizeof(nvsStore.get().ai_model));
        nvsStore.save_immediate();
    }
}

// -----------------------------------------------------------------------------
// 4. MÀN HÌNH CAPTIVE PORTAL AP MODE (KHI CHƯA CÓ WIFI)
// -----------------------------------------------------------------------------
void draw_ap_provisioning_screen() {
    tft.startWrite();
    tft.fillRect(0, 0, 240, 320, TFT_BLACK);

    tft.fillRect(0, 0, 240, 42, 0x0841);
    tft.setTextColor(TFT_WHITE, 0x0841);
    tft.setTextSize(1);
    tft.setCursor(12, 6);
    tft.println("NALA SMART HOME");

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(12, 22, "CHẾ ĐỘ CÀI ĐẶT WIFI (SOFT-AP)", 0x07E0);

    tft.drawRoundRect(8, 48, 224, 186, 6, 0x07E0);
    tft.fillRect(9, 49, 222, 184, 0x10A2);

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(16, 56, "BƯỚC 1: KẾT NỐI WIFI", TFT_YELLOW);
    fontMaker.print_noBackColor(16, 74, "SSID: " + captivePortal.get_ap_ssid(), 0x07FF);

    fontMaker.print_noBackColor(16, 102, "BƯỚC 2: MỞ TRÌNH DUYỆT", TFT_YELLOW);
    fontMaker.print_noBackColor(16, 120, "Truy cập: 192.168.4.1", 0x07FF);

    fontMaker.print_noBackColor(16, 146, "BƯỚC 3: CÀI ĐẶT", TFT_YELLOW);
    fontMaker.print_noBackColor(16, 164, "Chọn WiFi nhà & Nhập mật khẩu", TFT_WHITE);
    fontMaker.print_noBackColor(16, 182, "Sau đó bấm LƯU & KẾT NỐI", TFT_WHITE);

    tft.setTextColor(TFT_SILVER, TFT_BLACK);
    tft.setCursor(12, 248);
    tft.printf("MAC: %s\n", device_mac.c_str());

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(12, 268, "MÃ SỐ GHI NHẬN: [" + pairing_code + "]", 0x07E0);
    fontMaker.print_noBackColor(12, 296, "Giữ nút BOOT 5s để Reset gốc", 0x8410);

    tft.endWrite();
}

void draw_connecting_screen() {
    tft.startWrite();
    tft.fillRect(0, 0, 240, 320, TFT_BLACK);
    tft.fillRect(0, 0, 240, 42, 0x0841);
    tft.setTextColor(TFT_WHITE, 0x0841);
    tft.setTextSize(1);
    tft.setCursor(12, 6);
    tft.println("NALA SMART HOME");

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(12, 22, "ĐANG KẾT NỐI WIFI NHÀ...", 0x07FF);

    tft.drawRoundRect(10, 58, 220, 145, 6, 0x07FF);
    tft.fillRect(11, 59, 218, 143, 0x10A2);

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(20, 72, "Đang kết nối tới mạng:", TFT_WHITE);
    fontMaker.set_font(Tahoma16);
    fontMaker.print_noBackColor(20, 94, nvsStore.get().wifi_ssid, TFT_YELLOW);

    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(20, 134, "Vui lòng chờ trong giây lát...", TFT_SILVER);

    fontMaker.set_font(Tahoma16);
    fontMaker.print_noBackColor(14, 240, "MÃ GHÉP NỐI: [" + pairing_code + "]", 0x07FF);
    fontMaker.set_font(Tahoma12);
    fontMaker.print_noBackColor(14, 275, ">> Chạm màn hình để đổi WiFi <<", 0xFBE0);
    tft.endWrite();
}

// -----------------------------------------------------------------------------
// 5. WEBSOCKET CALLBACKS & ĐĂNG KÝ VỚI SERVER NAS
// -----------------------------------------------------------------------------
void notify_settings_changed() {
    JsonDocument doc;
    doc["type"] = "settings_update";
    doc["source"] = device_mac;
    doc["payload"]["settings"]["brightness"] = nvsStore.get().lcd_brightness;
    doc["payload"]["settings"]["volume"] = nvsStore.get().speaker_volume;
    doc["payload"]["settings"]["mic_gain"] = nvsStore.get_mic_gain();
    doc["payload"]["settings"]["ring_on_call"] = nvsStore.get().ring_on_call;
    doc["payload"]["settings"]["ai_model"] = nvsStore.get().ai_model;
    doc["payload"]["settings"]["radar_enabled"] = nvsStore.get().radar_enabled;
    doc["payload"]["settings"]["radar_wake_dist"] = nvsStore.get().radar_wake_dist;
    doc["payload"]["settings"]["radar_wave_hangup"] = nvsStore.get().radar_wave_hangup;
    String out;
    serializeJson(doc, out);
    wsManager.send_text(out);
    Serial.println("[WS] Da gui cap nhat cai dat (settings_update) len NAS Hub!");
}

void send_device_registration() {
    JsonDocument doc;
    doc["type"] = "register";
    doc["payload"]["mac"] = device_mac;
    doc["payload"]["pairing_code"] = pairing_code;
    doc["payload"]["ip"] = WiFi.localIP().toString();
    doc["payload"]["model"] = "ES3C28P";
    doc["payload"]["room"] = nvsStore.get().room_name;
    doc["payload"]["firmware_version"] = CURRENT_FIRMWARE_VERSION;
    doc["payload"]["settings"]["brightness"] = nvsStore.get().lcd_brightness;
    doc["payload"]["settings"]["volume"] = nvsStore.get().speaker_volume;
    doc["payload"]["settings"]["mic_gain"] = nvsStore.get_mic_gain();
    doc["payload"]["settings"]["ring_on_call"] = nvsStore.get().ring_on_call;
    doc["payload"]["settings"]["ai_model"] = nvsStore.get().ai_model;
    doc["payload"]["settings"]["radar_enabled"] = nvsStore.get().radar_enabled;
    doc["payload"]["settings"]["radar_wake_dist"] = nvsStore.get().radar_wake_dist;
    doc["payload"]["settings"]["radar_wave_hangup"] = nvsStore.get().radar_wave_hangup;
    String out;
    serializeJson(doc, out);
    wsManager.send_text(out);
    Serial.println("[WS] Da gui goi tin dang ky thiet bi len NAS Hub!");
}

void on_ws_connected() {
    send_device_registration();
    wsManager.send_text("{\"type\":\"get_time\"}");
    if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        uiDashboard.set_ws_connected(true);
        xSemaphoreGive(lvgl_mutex);
    }
}

void on_ws_disconnected() {
    if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
        uiDashboard.set_ws_connected(false);
        xSemaphoreGive(lvgl_mutex);
    }
}

void on_ws_text(const String& type, const JsonDocument& doc) {
    if (type == "ota_start") {
        String ota_url = doc["url"] | "";
        size_t ota_size = doc["size"] | 0;
        String ota_ver = doc["version"] | "v2.5.0";
        Serial.printf("[WS] Nhan lenh OTA tu NAS Hub! URL: %s, Size: %u, Ver: %s\n", ota_url.c_str(), (unsigned int)ota_size, ota_ver.c_str());
        if (ota_url.length() > 0) {
            OTAManager::perform_ota(ota_url, ota_size, ota_ver, pairing_code, &fontMaker, &tft, &wsManager);
        }
        return;
    }
    if (type == "enter_ap" || type == "reset_wifi") {
        Serial.println("[WS] Nhan lenh tu Web Admin: Chuyen sang AP Mode 192.168.4.1!");
        nvsStore.factory_reset();
        delay(250);
        ESP.restart();
        return;
    }

    bool taken = false;
    if (lvgl_mutex != NULL) {
        taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(1000)) == pdTRUE);
    }

    // Đồng bộ thời gian thực từ NAS Hub vào RTC nội bộ ESP32Time (chỉ chạy khi server gửi epoch)
    unsigned long ep = 0;
    if (doc.containsKey("epoch")) {
        ep = doc["epoch"].as<unsigned long>();
    } else if (doc.containsKey("timestamp")) {
        ep = doc["timestamp"].as<unsigned long>();
    } else if (doc["payload"].is<JsonObject>() && doc["payload"].containsKey("epoch")) {
        ep = doc["payload"]["epoch"].as<unsigned long>();
    } else if (doc["payload"].is<JsonObject>() && doc["payload"].containsKey("timestamp")) {
        ep = doc["payload"]["timestamp"].as<unsigned long>();
    }

    if (ep > 1000000000) {
        rtc.setTime(ep);
        Serial.printf("[RTC] Dong bo gio thanh cong tu NAS Hub: %s - %s\n", 
                      rtc.getTime("%H:%M:%S").c_str(), rtc.getTime("%d/%m/%Y").c_str());
        if (taken && uiDashboard.is_screensaver_active()) {
            String time_str = rtc.getTime("%H:%M");
            String sec_str = rtc.getTime(":%S");
            int wday = rtc.getDayofWeek();
            const char* wday_names[7] = {"CHỦ NHẬT", "THỨ HAI", "THỨ BA", "THỨ TƯ", "THỨ NĂM", "THỨ SÁU", "THỨ BẢY"};
            const char* wday_name = (wday >= 0 && wday < 7) ? wday_names[wday] : "HÔM NAY";
            String date_str = rtc.getTime("%d/%m/%Y");
            uiDashboard.update_standby_clock(time_str.c_str(), sec_str.c_str(), wday_name, date_str.c_str());
        }
    }

    if (type == "time_sync") {
        if (taken) xSemaphoreGive(lvgl_mutex);
        return;
    }

    Serial.printf("[WS-TEXT] Handling type: %s, FreeHeap: %lu\n", type.c_str(), (unsigned long)ESP.getFreeHeap());
    if (type == "abort" || type == "tts_stop") {
        Serial.println("[AI] Nhan lenh abort/tts_stop tu Server Hub -> Dung phat va xa DMA!");
        audioEngine.stop_playback();
        audioEngine.enable_mic(true);
        rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Trở lại xanh lá
        rgb_led.show();
        if (taken) {
            uiDashboard.set_ai_state("idle", "");
            xSemaphoreGive(lvgl_mutex);
        }
        return;
    } else if (type == "tts") {
        String st = doc["state"] | "";
        if (st == "sentence_start") {
            String sent_txt = doc["text"] | "";
            int sent_idx = doc["index"] | 0;
            Serial.printf("[AI TTS] sentence_start #%d: %s\n", sent_idx, sent_txt.c_str());
            if (taken) {
                uiDashboard.set_ai_sentence(sent_txt.c_str());
                xSemaphoreGive(lvgl_mutex);
            }
            return;
        } else if (st == "stop") {
            audioEngine.stop_playback();
            if (taken) {
                uiDashboard.set_ai_state("idle", "");
                xSemaphoreGive(lvgl_mutex);
            }
            return;
        }
    } else if (type == "sentence_start") {
        String sent_txt = doc["payload"]["text"] | doc["text"] | "";
        int sent_idx = doc["payload"]["index"] | doc["index"] | 0;
        Serial.printf("[AI] sentence_start #%d: %s\n", sent_idx, sent_txt.c_str());
        if (taken) {
            uiDashboard.set_ai_sentence(sent_txt.c_str());
            xSemaphoreGive(lvgl_mutex);
        }
        return;
    } else if (type == "wake_trigger") {
        static unsigned long last_wake_trigger = 0;
        if (millis() - last_wake_trigger < 1500) {
            if (taken) xSemaphoreGive(lvgl_mutex);
            return;
        }
        last_wake_trigger = millis();

        Serial.println("[AI] Nhan lenh thuc tinh Wake Word Trigger (Hey Nala)!");

        // 1. Phản hồi thị giác tức thì < 5ms: Bật LED Cyan + Thoát Standby + Mở Tab AI + Mochi Listening + Phụ đề
        rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 200)); // Xanh ngọc cyan
        rgb_led.show();

        if (taken) {
            uiDashboard.hide_screensaver();
            uiDashboard.switch_to_ai_tab();
            
            float w_score = doc["score"] | 0.0f;
            char state_str[48];
            if (w_score > 0.01f) {
                int sc_pct = (int)round(w_score * 100.0f);
                if (sc_pct > 100) sc_pct = 100;
                snprintf(state_str, sizeof(state_str), "Đang nghe... (%d%%)", sc_pct);
            } else {
                snprintf(state_str, sizeof(state_str), "Đang nghe...");
            }
            uiDashboard.set_ai_state("listening", state_str);
            uiDashboard.set_ai_text("Em nghe!");
            xSemaphoreGive(lvgl_mutex);
            taken = false; // Đã nhả mutex để Task LVGL render khung hình ngay lập tức
        }

        // 2. Chế độ Xiaozhi: Đặt cờ chờ Server stream câu chào "Em nghe!" phát xong mới mở mic
        audioEngine.stop_playback();
        wake_trigger_start_ms = millis();
        is_waiting_wake_speech = true;
        is_recording_ptt = false; // Đảm bảo Mic tắt hoàn toàn khi đang phát câu chào "Em nghe!"
        audioEngine.enable_mic(false);
        return;
    } else if (type == "start_listen") {
        uint32_t t_ms = doc["payload"]["timeout_ms"] | 8000;
        Serial.printf("[CONTINUOUS] Nhan lenh tu dong mo Mic nghe tiep (timeout=%lu ms)\n", (unsigned long)t_ms);
        rgb_led.setPixelColor(0, rgb_led.Color(0, 200, 255)); // Xanh lơ cyan
        rgb_led.show();
        if (taken) {
            uiDashboard.hide_screensaver();
            uiDashboard.switch_to_ai_tab();
            uiDashboard.set_ai_state("listening", "Đang nghe tiếp...");
            xSemaphoreGive(lvgl_mutex);
            taken = false;
        }
        audioEngine.stop_playback();
        audioEngine.mute_speaker(false);
        // Chế độ Xiaozhi: KHÔNG phát chuông Ding để tránh mic tự thu lại tiếng chuông gây vòng lặp suy nghĩ vô tận!
        is_continuous_listening = true;
        continuous_listen_start = millis();
        continuous_listen_timeout_ms = t_ms;
        is_hands_free_session = true;
        hands_free_start_time = millis();
        hands_free_last_voice = 0; // Chưa có giọng nói, chờ người dùng cất lời
        is_recording_ptt = true;
        ptt_target_id = TARGET_ID_AI_SERVER;
        ptt_start_flag = true;
        audioEngine.enable_mic(true);
        return;
    } else if (type == "wake_suppress" || (type == "wake_event" && doc["payload"]["status"] == "suppressed")) {
        Serial.println("[AI] Phòng khác đã tiếp nhận Wake Word (Suppressing)...");
    } else if (type == "wake_chime") {
        Serial.println("[AI] Nhan lenh phat am thanh thuc tinh Ding!");
        audioEngine.stop_playback(); // Xả sạch DMA trước khi phát nốt Ding
        audioEngine.play_wake_chime();
        if (taken) {
            uiDashboard.hide_screensaver();
            uiDashboard.switch_to_ai_tab();
            uiDashboard.set_ai_state("listening", "Đang nghe...");
        }
    } else if (type == "ack_chime") {
        Serial.println("[AI] Nhan lenh phat am thanh nhan lenh Poong!");
        audioEngine.play_ack_chime();
        if (taken) uiDashboard.set_ai_state("thinking", "Đang xử lý...");
    } else if (type == "done_chime") {
        Serial.println("[AI] Nhan lenh phat am thanh hoan thanh Ting!");
        audioEngine.play_done_chime();
    } else if (type == "wake_config_update") {
        const char* new_wake = doc["payload"]["wake_word"] | "";
        if (new_wake && strlen(new_wake) > 0 && taken) {
            uiDashboard.set_wake_word_name(new_wake);
        }
        return;
    } else if (type == "ai_state") {
        String state = doc["payload"]["state"] | "IDLE";
        String txt = doc["payload"]["text"] | "";
        if (state.equalsIgnoreCase("idle")) {
            audioEngine.enable_mic(true);
        }
        if (taken) {
            if (state == "listening" || state == "speaking" || state == "thinking") {
                uiDashboard.hide_screensaver();
                uiDashboard.switch_to_ai_tab();
            }
            uiDashboard.set_ai_state(state.c_str(), txt.c_str());
        }
    } else if (type == "config_sync") {
        uint8_t assigned_id = doc["payload"]["my_intercom_id"] | 0;
        if (assigned_id > 0) {
            my_intercom_id = assigned_id;
            Serial.printf("[INTERCOM] Assigned My Intercom ID: 0x%02X (%d)\n", my_intercom_id, my_intercom_id);
        }
        JsonArrayConst targets = doc["payload"]["intercom_targets"];
        if (targets.size() > 0 && taken) {
            uiDashboard.sync_intercom_targets(targets);
        }

        const char* new_wake = doc["payload"]["wake_word"] | "";
        if (new_wake && strlen(new_wake) > 0 && taken) {
            uiDashboard.set_wake_word_name(new_wake);
        }

        String new_room = doc["payload"]["room"] | "";
        if (new_room.length() > 0) {
            if (strcmp(nvsStore.get().room_name, new_room.c_str()) != 0) {
                strncpy(nvsStore.get().room_name, new_room.c_str(), sizeof(nvsStore.get().room_name));
                nvsStore.mark_dirty();
            }
            Serial.printf("[SYNC] Da dong bo ten phong moi: %s\n", new_room.c_str());
            if (taken) uiDashboard.set_room_title(new_room.c_str());
        }

        JsonArrayConst buttons = doc["payload"]["buttons"];
        if (buttons.size() > 0 && taken) {
            Serial.printf("[MAIN] Before sync_buttons: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_buttons(buttons);
            Serial.printf("[MAIN] After sync_buttons: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
        }
        if (doc["payload"].containsKey("all_rooms") && taken) {
            Serial.printf("[MAIN] Before sync_all_rooms: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_all_rooms(doc["payload"]["all_rooms"]);
            Serial.printf("[MAIN] After sync_all_rooms: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
        }
        if (doc["payload"].containsKey("house_status") && taken) {
            Serial.printf("[MAIN] Before sync_house_status: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_house_status(doc["payload"]["house_status"]);
            Serial.printf("[MAIN] After sync_house_status: FreeHeap=%lu\n", (unsigned long)ESP.getFreeHeap());
        }

        if (doc["payload"].containsKey("settings")) {
            JsonObjectConst st = doc["payload"]["settings"];
            bool changed = false;
            if (st.containsKey("brightness")) {
                uint8_t br = st["brightness"] | nvsStore.get().lcd_brightness;
                if (br != nvsStore.get().lcd_brightness) {
                    nvsStore.get().lcd_brightness = br;
                    tft.setBrightness(br);
                    changed = true;
                }
            }
            if (st.containsKey("volume")) {
                uint8_t vl = st["volume"] | nvsStore.get().speaker_volume;
                if (vl != nvsStore.get().speaker_volume) {
                    nvsStore.get().speaker_volume = vl;
                    audioEngine.set_speaker_volume(vl);
                    changed = true;
                }
            }
            if (st.containsKey("mic_gain")) {
                uint8_t mg = st["mic_gain"] | nvsStore.get_mic_gain();
                if (mg != nvsStore.get_mic_gain()) {
                    nvsStore.set_mic_gain(mg);
                    audioEngine.set_mic_gain(mg);
                    changed = true;
                }
            }
            if (st.containsKey("ring_on_call")) {
                bool rc = st["ring_on_call"] | nvsStore.get().ring_on_call;
                if (rc != nvsStore.get().ring_on_call) {
                    nvsStore.get().ring_on_call = rc;
                    changed = true;
                }
            }
            if (st.containsKey("ai_model")) {
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
            }
            if (st.containsKey("standby_timeout")) {
                uint16_t sto = st["standby_timeout"] | 30;
                if (sto != nvsStore.get().standby_timeout) {
                    nvsStore.get().standby_timeout = sto;
                    changed = true;
                }
            }
            if (st.containsKey("radar_enabled")) {
                bool re = st["radar_enabled"];
                if (re != nvsStore.get().radar_enabled) {
                    nvsStore.get().radar_enabled = re;
                    changed = true;
                }
            }
            if (st.containsKey("radar_wake_dist")) {
                uint16_t rwd = st["radar_wake_dist"] | 150;
                if (rwd != nvsStore.get().radar_wake_dist) {
                    nvsStore.get().radar_wake_dist = rwd;
                    changed = true;
                }
            }
            if (st.containsKey("radar_wave_hangup")) {
                bool rwh = st["radar_wave_hangup"];
                if (rwh != nvsStore.get().radar_wave_hangup) {
                    nvsStore.get().radar_wave_hangup = rwh;
                    changed = true;
                }
            }

            if (changed) {
                nvsStore.save_immediate();
            }
            if (taken) {
                uiDashboard.sync_settings(
                    nvsStore.get().speaker_volume,
                    nvsStore.get().lcd_brightness,
                    nvsStore.get().ring_on_call,
                    nvsStore.get_mic_gain()
                );
            }
        }
    } else if (type == "intercom_sync") {
        uint8_t assigned_id = doc["payload"]["my_intercom_id"] | 0;
        if (assigned_id > 0) my_intercom_id = assigned_id;
        JsonArrayConst targets = doc["payload"]["targets"];
        if (taken) uiDashboard.sync_intercom_targets(targets);
    } else if (type == "intercom_call_started") {
        uint8_t target_ic_id = doc["target_intercom_id"] | (doc["payload"]["target_intercom_id"] | 0);
        const char* t_name = doc["target_room"] | (doc["payload"]["target_room"] | "Phòng khác");
        is_intercom_call_active = true;
        intercom_peer_id = target_ic_id;
        strncpy(intercom_peer_name, t_name, sizeof(intercom_peer_name) - 1);
        ptt_target_id = target_ic_id;
        is_recording_ptt = false; // Chờ filler TTS "Đang kết nối..." phát xong rồi mới nhả mic
        if (taken) {
            uiDashboard.hide_screensaver();
            uiDashboard.show_incoming_call(t_name, false);
            uiDashboard.set_intercom_status("Đang kết nối...", 0x38BDF8);
        }
        rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương
        rgb_led.show();
        Serial.printf("[INTERCOM] Call started to target ID 0x%02X (%s)\n", target_ic_id, t_name);
    } else if (type == "intercom_incoming_call") {
        uint8_t caller_ic_id = doc["caller_intercom_id"] | (doc["payload"]["caller_intercom_id"] | 0);
        const char* c_name = doc["caller_room"] | (doc["payload"]["caller_room"] | "Phòng khác");
        bool auto_ans = doc["auto_answer"] | (doc["payload"]["auto_answer"] | true);
        is_intercom_call_active = true;
        intercom_peer_id = caller_ic_id;
        strncpy(intercom_peer_name, c_name, sizeof(intercom_peer_name) - 1);
        ptt_target_id = caller_ic_id;
        if (taken) {
            uiDashboard.hide_screensaver();
            uiDashboard.show_incoming_call(c_name, true);
            uiDashboard.set_intercom_status("Cuộc gọi đến...", 0xF59E0B);
        }
        rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255));
        rgb_led.show();
        audioEngine.mute_speaker(false);
        audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
        audioEngine.play_ringtone();
        if (auto_ans) {
            if (taken) {
                uiDashboard.show_incoming_call(c_name, false);
                uiDashboard.set_intercom_status("Đang đàm thoại: Sẵn sàng", 0x10B981);
            }
            audioEngine.enable_mic(true);
            is_recording_ptt = true;
            ptt_start_flag = true;
            ptt_target_id = caller_ic_id;
        }
        Serial.printf("[INTERCOM] Incoming call from ID 0x%02X (%s) - Auto answer: %d\n", caller_ic_id, c_name, auto_ans);
    } else if (type == "intercom_hangup") {
        is_intercom_call_active = false;
        intercom_peer_id = 0x00;
        is_recording_ptt = false;
        if (taken) {
            uiDashboard.hide_incoming_call();
            uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
        }
        rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá
        rgb_led.show();
        audioEngine.play_wake_chime();
        Serial.println("[INTERCOM] Cuộc gọi đã kết thúc (intercom_hangup).");
    } else if (type == "intercom_silence_warning") {
        Serial.println("[INTERCOM] Cảnh báo im lặng 10s sắp cúp máy!");
        audioEngine.play_wake_chime();
    } else if (type == "ha_state_change") {
        String entity_id = doc["payload"]["entity_id"] | "";
        String state = doc["payload"]["state"] | "";
        bool is_on = false;
        if (doc["payload"].containsKey("is_on")) {
            is_on = doc["payload"]["is_on"] | false;
        } else {
            is_on = (state == "on" || (state != "off" && state != "unavailable" && state != "unknown" && state.length() > 0));
        }
        float temp = 0.0f;
        float current_temp = 0.0f;
        String hvac_mode = (state != "off" && state != "unavailable" && state != "unknown") ? state : "off";
        String fan_mode = "";
        int swing = -1;
        if (doc["payload"].containsKey("attributes")) {
            JsonObjectConst attrs = doc["payload"]["attributes"];
            if (attrs.containsKey("temperature")) temp = attrs["temperature"] | 0.0f;
            if (attrs.containsKey("current_temperature")) current_temp = attrs["current_temperature"] | 0.0f;
            if (attrs.containsKey("hvac_mode")) hvac_mode = attrs["hvac_mode"] | hvac_mode;
            if (attrs.containsKey("fan_mode")) fan_mode = attrs["fan_mode"] | "";
            if (attrs.containsKey("swing_mode")) {
                String sm = attrs["swing_mode"] | "";
                swing = (sm != "off" && sm.length() > 0) ? 1 : 0;
            }
        }
        Serial.printf("[HA-SYNC] %s -> state: %s, on: %d, temp: %.1f, room: %.1f, fan: %s\n",
                      entity_id.c_str(), state.c_str(), is_on, temp, current_temp, fan_mode.c_str());
        if (taken) {
            uiDashboard.update_entity_state(entity_id.c_str(), is_on, temp, current_temp,
                                            hvac_mode.c_str(), fan_mode.c_str(), swing);
            if (doc["payload"].containsKey("house_status")) {
                uiDashboard.sync_house_status(doc["payload"]["house_status"]);
            }
            if (doc["payload"].containsKey("all_rooms")) {
                uiDashboard.sync_all_rooms(doc["payload"]["all_rooms"]);
            }
        }
    } else if (type == "pong") {
        unsigned long now = millis();
        unsigned long client_time = doc["client_time"] | ws_ping_start_ms;
        unsigned long rtt = (now >= client_time) ? (now - client_time) : 0;
        char buf[64];
        snprintf(buf, sizeof(buf), "Server: Kết nối OK (%lu ms)", rtt);
        if (taken) uiDashboard.set_diag_result(buf, 0x10B981);
        Serial.printf("[DIAG] Pong received: RTT = %lu ms\n", rtt);
    }

    if (taken) xSemaphoreGive(lvgl_mutex);
}

// Nhận Audio Binary 520 Byte từ Server NAS phát ra Loa
void on_ws_binary(const uint8_t* data, size_t len) {
    if (len == BINARY_PACKET_SIZE) {
        const AudioPacket_t* p = (const AudioPacket_t*)data;
        if (p->magic == BINARY_MAGIC_WORD) {
            // Half-duplex: Nếu đang giữ nút nói thì không phát để chống feedback
            if (is_recording_ptt) return;

            // Phân biệt: sender_id == 0x00 là âm thanh phản hồi từ AI Nala / Server Hub
            // sender_id >= 0x01 là cuộc gọi Intercom đàm thoại nội bộ giữa các phòng
            bool is_ai_or_server = (p->sender_id == 0x00);

            if (p->stream_flag == STREAM_FLAG_START) {
                if (!is_ai_or_server) {
                    char caller_buf[64];
                    uiDashboard.get_caller_display(p->sender_id, caller_buf, sizeof(caller_buf));
                    bool ring = nvsStore.get().ring_on_call;

                    bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                    if (taken) {
                        uiDashboard.show_incoming_call(caller_buf, ring);
                        uiDashboard.set_intercom_status("Cuộc gọi đến...", 0xF59E0B);
                        xSemaphoreGive(lvgl_mutex);
                    }

                    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương (Intercom)
                    rgb_led.show();

                    audioEngine.mute_speaker(false);
                    audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
                    if (ring) {
                        audioEngine.play_ringtone(); // Đổ chuông du dương Ding-Dong to rõ
                        taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                        if (taken) {
                            uiDashboard.show_incoming_call(caller_buf, false);
                            xSemaphoreGive(lvgl_mutex);
                        }
                    }
                    Serial.printf("[INTERCOM] Cuộc gọi đến từ ID 0x%02X (%s) - Đổ chuông: %d\n", p->sender_id, caller_buf, ring);
                } else {
                    // Âm thanh phản hồi từ AI Nala: KHÔNG hiện popup cuộc gọi nội bộ, KHÔNG đổ chuông intercom
                    rgb_led.setPixelColor(0, rgb_led.Color(56, 189, 248)); // Xanh lơ (Sky blue - AI Voice)
                    rgb_led.show();

                    audioEngine.mute_speaker(false);
                    audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
                    Serial.println("[AI VOICE] Nhận âm thanh phản hồi từ AI Nala (không hiện popup intercom)...");
                }
            } else {
                audioEngine.mute_speaker(false);
            }

            // Phát âm thanh stereo ra Loa qua I2S DMA
            int16_t stereo_out[AUDIO_FRAME_SAMPLES * 2];
            for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                int16_t val = p->pcm_data[s];
                stereo_out[s * 2]     = val;
                stereo_out[s * 2 + 1] = val;
            }
            size_t written = 0;
            i2s_write(I2S_NUM_0, stereo_out, sizeof(stereo_out), &written, portMAX_DELAY);
            last_speaker_active_ms = millis();

            if (p->stream_flag == STREAM_FLAG_END) {
                delay(120); // Đợi 120ms để DMA phát hết trọn vẹn từ cuối câu trước khi ngắt amply
                audioEngine.mute_speaker(true);
                last_speaker_active_ms = millis();

                if (is_waiting_wake_speech) {
                    // Luồng Xiaozhi: Đã nói xong "Dạ, em nghe!" -> Mở Micro thu âm câu lệnh người dùng tức thì!
                    is_waiting_wake_speech = false;
                    audioEngine.enable_mic(true);
                    is_hands_free_session = true;
                    hands_free_start_time = millis();
                    hands_free_last_voice = 0; // Chờ người dùng cất tiếng nói
                    is_recording_ptt = true;
                    ptt_target_id = TARGET_ID_AI_SERVER;
                    ptt_start_flag = true;

                    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 200)); // Xanh ngọc Cyan lắng nghe
                    rgb_led.show();

                    bool taken_ui = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(40)) == pdTRUE);
                    if (taken_ui) {
                        uiDashboard.set_ai_state("listening", "Đang nghe...");
                        uiDashboard.set_ai_text("Đang nghe bạn nói...");
                        xSemaphoreGive(lvgl_mutex);
                    }
                    Serial.println("[AI] Đã phát xong câu chào 'Dạ, em nghe' -> Bắt đầu thu âm lệnh người dùng!");
                } else if (is_intercom_call_active && is_ai_or_server) {
                    // Đã phát xong câu chào "Dạ, đang kết nối với..." -> Bật mic đàm thoại rảnh tay!
                    audioEngine.enable_mic(true);
                    is_recording_ptt = true;
                    ptt_start_flag = true;
                    ptt_target_id = intercom_peer_id;
                    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương Intercom
                    rgb_led.show();
                    bool taken_ui = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(40)) == pdTRUE);
                    if (taken_ui) {
                        uiDashboard.show_incoming_call(intercom_peer_name, false);
                        uiDashboard.set_intercom_status("Đang đàm thoại: Sẵn sàng", 0x10B981);
                        xSemaphoreGive(lvgl_mutex);
                    }
                    Serial.printf("[INTERCOM] Caller đã sẵn sàng đàm thoại với ID 0x%02X!\n", intercom_peer_id);
                } else {
                    if (is_intercom_call_active) {
                        rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Giữ xanh dương
                        rgb_led.show();
                    } else {
                        rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Trở lại xanh lá
                        rgb_led.show();
                    }

                    if (!is_ai_or_server && !is_intercom_call_active) {
                        bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                        if (taken) {
                            uiDashboard.hide_incoming_call();
                            uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                            xSemaphoreGive(lvgl_mutex);
                        }
                        Serial.println("[INTERCOM] Kết thúc cuộc gọi.");
                    } else if (is_ai_or_server && !is_intercom_call_active) {
                        Serial.println("[AI VOICE] Đã phát xong âm thanh AI Nala.");
                        audioEngine.enable_mic(true);
                        bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                        if (taken) {
                            uiDashboard.set_ai_state("idle", "");
                            uiDashboard.set_ai_sentence("");
                            xSemaphoreGive(lvgl_mutex);
                        }
                    }
                }
            }
        }
    }
}

// -----------------------------------------------------------------------------
// 6. THU ÂM I2S DMA STREAMING (CORE 0)
// -----------------------------------------------------------------------------
void handle_mic_streaming() {
    static uint16_t seq = 0;
    static int16_t stereo_raw[AUDIO_FRAME_SAMPLES * 2]; // 512 int16_t = 1024 bytes (256 L + 256 R)
    static bool was_recording = false;
    size_t bytes_read = 0;

    // Timeout Fallback: Nếu sau 1500ms không nhận được audio chào từ Server Hub, tự phát chuông ding và mở mic
    if (is_waiting_wake_speech && (millis() - wake_trigger_start_ms > 1500)) {
        is_waiting_wake_speech = false;
        audioEngine.enable_mic(true);
        audioEngine.play_wake_chime();
        is_hands_free_session = true;
        hands_free_start_time = millis();
        hands_free_last_voice = 0;
        is_recording_ptt = true;
        ptt_target_id = TARGET_ID_AI_SERVER;
        ptt_start_flag = true;
        Serial.println("[AI] Timeout chờ audio chào -> Tự mở mic thu âm fallback!");
    }

    // -------------------------------------------------------------
    // CHẾ ĐỘ ĐÀM THOẠI RẢNH TAY LIÊN PHÒNG (HANDS-FREE INTERCOM V2)
    // -------------------------------------------------------------
    if (is_intercom_call_active) {
        // Voice-Switching: Khi loa đang phát âm thanh từ phòng đối phương (+ 180ms release) -> MUTE MIC để triệt tiêu vòng lặp âm học!
        if (millis() - last_speaker_active_ms < 180) {
            vTaskDelay(pdMS_TO_TICKS(10));
            return;
        }

        esp_err_t res = i2s_read(I2S_NUM_0, stereo_raw, sizeof(stereo_raw), &bytes_read, pdMS_TO_TICKS(25));
        if (res == ESP_OK && bytes_read == sizeof(stereo_raw)) {
            AudioPacket_t pkt;
            pkt.magic = BINARY_MAGIC_WORD;
            pkt.sender_id = my_intercom_id;
            pkt.target_id = intercom_peer_id;
            pkt.seq_num = seq++;
            pkt.stream_flag = ptt_start_flag ? STREAM_FLAG_START : STREAM_FLAG_DATA;
            ptt_start_flag = false;

            uint8_t gain_setting = nvsStore.get_mic_gain();
            int32_t sw_boost = (int32_t)(gain_setting * 2 + 6);
            int64_t ssq = 0;

            for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                int16_t sample_l = stereo_raw[s * 2];
                int16_t sample_r = stereo_raw[s * 2 + 1];
                int16_t raw_sample = (abs((int)sample_l) >= abs((int)sample_r)) ? sample_l : sample_r;
                int32_t boosted = (int32_t)raw_sample * sw_boost;
                if (boosted > 28000) boosted = 28000;
                else if (boosted < -28000) boosted = -28000;
                pkt.pcm_data[s] = (int16_t)boosted;
                ssq += ((int32_t)boosted * (int32_t)boosted);
            }

            int32_t cur_rms = (int32_t)sqrt(ssq / AUDIO_FRAME_SAMPLES);
            // Chỉ gửi gói tin âm thanh khi có người nói (RMS >= 70) để triệt tiêu tiếng ồn nền và giữ yên lặng khi không ai nói
            if (cur_rms >= 70) {
                pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
                wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
            }
        }
        return;
    }

    if (is_recording_ptt) {
        if (!was_recording) {
            was_recording = true;
            // Xả bỏ 1 khung DMA cũ lúc vừa bật Mic
            size_t dummy_bytes = 0;
            i2s_read(I2S_NUM_0, stereo_raw, sizeof(stereo_raw), &dummy_bytes, pdMS_TO_TICKS(10));
        }

        // Đọc 256 khung Stereo (1024 bytes = 16ms âm thanh) từ I2S DMA
        esp_err_t res = i2s_read(I2S_NUM_0, stereo_raw, sizeof(stereo_raw), &bytes_read, pdMS_TO_TICKS(30));
        if (res == ESP_OK && bytes_read == sizeof(stereo_raw)) {
            AudioPacket_t pkt;
            pkt.magic = BINARY_MAGIC_WORD;
            pkt.sender_id = my_intercom_id; // Dynamic Intercom ID
            pkt.target_id = ptt_target_id;
            pkt.seq_num = seq++;
            pkt.stream_flag = ptt_start_flag ? STREAM_FLAG_START : STREAM_FLAG_DATA;
            ptt_start_flag = false;

            uint8_t gain_setting = nvsStore.get_mic_gain();
            int32_t sw_boost = (int32_t)(gain_setting * 2 + 6); // Đồng bộ 8x..20x khuếch đại số

            // ES8311 Mono ADC xuất âm thanh trên kênh Trái (Left)
            for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                int16_t sample_l = stereo_raw[s * 2];
                int16_t sample_r = stereo_raw[s * 2 + 1];
                int16_t raw_sample = (abs((int)sample_l) >= abs((int)sample_r)) ? sample_l : sample_r;

                // Khuếch đại giọng nói kỹ thuật số theo cài đặt NVS kèm soft limiter chống vỡ tiếng
                int32_t boosted = (int32_t)raw_sample * sw_boost;
                if (boosted > 28000) boosted = 28000;
                else if (boosted < -28000) boosted = -28000;
                pkt.pcm_data[s] = (int16_t)boosted;
            }

            // Tự động ngắt thu âm rảnh tay khi phát hiện im lặng (Silence VAD)
            if (is_hands_free_session) {
                int64_t ssq = 0;
                for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                    int32_t val = pkt.pcm_data[s];
                    ssq += (val * val);
                }
                int32_t cur_rms = (int32_t)sqrt(ssq / AUDIO_FRAME_SAMPLES);
                unsigned long now = millis();
                if (cur_rms >= 85) { // Nguong bat tieng noi nhay (85 RMS tuong duong 75 cua Wake Scan), bat tron ven giong noi tu 1 - 2.5m
                    hands_free_last_voice = now;
                    if (is_continuous_listening) {
                        is_continuous_listening = false; // Người dùng đã cất tiếng nói, bắt đầu thu âm lệnh!
                    }
                }

                // 1. Trường hợp chờ câu nói tiếp theo (Continuous Listening) mà hết timeout (mặc định 8s) không có ai nói
                if (is_continuous_listening && (hands_free_last_voice == 0) && (now - continuous_listen_start > continuous_listen_timeout_ms)) {
                    Serial.printf("[CONTINUOUS] Het thoi gian cho (%lu ms) khong co tieng noi -> Chao tam biet.\n", (unsigned long)continuous_listen_timeout_ms);
                    is_recording_ptt = false;
                    is_hands_free_session = false;
                    is_continuous_listening = false;
                    was_recording = false; // QUAN TRỌNG: Đặt false để KHÔNG gửi STREAM_FLAG_END kéo theo âm thanh rác
                    seq = 0;
                    audioEngine.enable_mic(true);

                    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá
                    rgb_led.show();

                    bool taken_ui = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(30)) == pdTRUE);
                    if (taken_ui) {
                        uiDashboard.set_ai_state("idle", "");
                        uiDashboard.set_ai_sentence("");
                        xSemaphoreGive(lvgl_mutex);
                    }
                    wsManager.send_text("{\"type\":\"listen_timeout\"}");
                }
                // 2. Trường hợp vừa kích hoạt Wake Word nhưng quá 6s không có ai nói gì -> Tự động kết thúc phiên và về IDLE
                else if (!is_continuous_listening && (hands_free_last_voice == 0) && (now - hands_free_start_time > 6000)) {
                    Serial.println("[VAD] Khong phat hien giong noi sau Wake Word (6s) -> Ket thuc phien!");
                    is_recording_ptt = false;
                    is_hands_free_session = false;
                    was_recording = false; // QUAN TRỌNG: Đặt false để KHÔNG gửi STREAM_FLAG_END kéo theo âm thanh rác
                    seq = 0;
                    audioEngine.enable_mic(true);

                    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá idle
                    rgb_led.show();
                    bool taken_ui = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(30)) == pdTRUE);
                    if (taken_ui) {
                        uiDashboard.set_ai_state("idle", "");
                        uiDashboard.set_ai_text("Sẵn sàng lắng nghe...");
                        xSemaphoreGive(lvgl_mutex);
                    }
                    wsManager.send_text("{\"type\":\"listen_timeout\"}");
                }
                // 3. Trường hợp đã nói (hands_free_last_voice > 0), sau đó im lặng quá 380ms (hoặc max 7s) -> Ngắt thu âm siêu tốc, chuyển sang xử lý!
                else if (hands_free_last_voice > 0 && ((now - hands_free_last_voice > 380 && now - hands_free_start_time > 420) || (now - hands_free_start_time > 7500))) {
                    Serial.println("[VAD] Phat hien im lang (380ms) / het cau lenh -> Tu dong ket thuc thu am sieu toc!");
                    is_recording_ptt = false;
                    is_hands_free_session = false;
                    is_continuous_listening = false;
                    bool taken_ui = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(30)) == pdTRUE);
                    if (taken_ui) {
                        uiDashboard.set_ai_state("thinking", "Đang xử lý...");
                        xSemaphoreGive(lvgl_mutex);
                    }
                }
            }

            // CHỐNG RÁC & ẢO GIÁC: Nếu người dùng chưa cất tiếng nói (hands_free_last_voice == 0), TUYỆT ĐỐI KHÔNG gửi audio lên Server!
            if (is_hands_free_session && hands_free_last_voice == 0) {
                // Đang đếm ngược chờ người dùng nói, không truyền audio im lặng/nhiễu nền lên Server!
            } else {
                pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
                wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
            }
        }
    } else if (was_recording) {
        was_recording = false;
        if (seq > 0) {
            AudioPacket_t pkt;
            memset(&pkt, 0, sizeof(AudioPacket_t));
            pkt.magic = BINARY_MAGIC_WORD;
            pkt.sender_id = my_intercom_id;
            pkt.target_id = ptt_target_id;
            pkt.seq_num = seq++;
            pkt.stream_flag = STREAM_FLAG_END; // 0x03
            pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
            wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
            Serial.println("[AUDIO] Da gui goi ket thuc STREAM_FLAG_END (0x03) len Server NAS!");
            seq = 0;
        }
    } else {
        // Chế độ Nghe Rảnh Tay Năng Lượng Thấp với Pre-Roll Buffer (Smart Energy VAD)
        static unsigned long last_voice_activity = 0;
        static bool is_wake_streaming = false;
        static uint16_t wake_seq = 0;

        if (nvsStore.get().wake_word_enabled && wsManager.is_connected()) {
            // Chống Loa tự thu vào Mic gây vòng lặp Wake Word (Acoustic Echo Suppression)
            if (millis() - last_speaker_active_ms < 1200) {
                wake_ring_count = 0;
                is_wake_streaming = false;
                vTaskDelay(pdMS_TO_TICKS(10));
                return;
            }

            esp_err_t res = i2s_read(I2S_NUM_0, stereo_raw, sizeof(stereo_raw), &bytes_read, pdMS_TO_TICKS(25));
            if (res == ESP_OK && bytes_read == sizeof(stereo_raw)) {
                int64_t sum_sq = 0;
                int16_t pcm_boosted[AUDIO_FRAME_SAMPLES];
                uint8_t gain_setting = nvsStore.get_mic_gain();
                int32_t sw_boost = (int32_t)(gain_setting * 2 + 6);

                for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                    int16_t sample_l = stereo_raw[s * 2];
                    int16_t sample_r = stereo_raw[s * 2 + 1];
                    int16_t raw_sample = (abs((int)sample_l) >= abs((int)sample_r)) ? sample_l : sample_r;
                    int32_t boosted = (int32_t)raw_sample * sw_boost;
                    if (boosted > 28000) boosted = 28000;
                    else if (boosted < -28000) boosted = -28000;
                    pcm_boosted[s] = (int16_t)boosted;
                    sum_sq += ((int32_t)boosted * (int32_t)boosted);
                }

                int32_t rms = (int32_t)sqrt(sum_sq / AUDIO_FRAME_SAMPLES);
                unsigned long now = millis();

                // Lưu khung âm thanh vào Pre-Roll Circular Buffer trong PSRAM
                if (wake_preroll_buf) {
                    memcpy(wake_preroll_buf[wake_ring_head], pcm_boosted, sizeof(pcm_boosted));
                    wake_ring_head = (wake_ring_head + 1) % WAKE_PREROLL_FRAMES;
                    if (wake_ring_count < WAKE_PREROLL_FRAMES) wake_ring_count++;
                }

                // Ngưỡng phát hiện tiếng nói siêu nhạy: rms >= 75 (~22dBFS)
                if (rms >= 75) {
                    last_voice_activity = now;
                    if (!is_wake_streaming) {
                        is_wake_streaming = true;
                        wake_seq = 0;
                        Serial.printf("[WAKE-VAD] Voice detected! RMS: %d (nguong: 75) -> Xa 560ms Pre-Roll\n", (int)rms);

                        // Xả sạch 560ms âm thanh đệm quá khứ (Pre-Roll) lên Server để nhận diện trọn vẹn từ đầu!
                        if (wake_preroll_buf && wake_ring_count > 0) {
                            uint8_t read_idx = (wake_ring_head + WAKE_PREROLL_FRAMES - wake_ring_count) % WAKE_PREROLL_FRAMES;
                            for (uint8_t f = 0; f < wake_ring_count; f++) {
                                AudioPacket_t wpkt;
                                wpkt.magic = BINARY_MAGIC_WORD; // 0xA55A
                                wpkt.sender_id = my_intercom_id;
                                wpkt.target_id = 0x05; // Target 0x05: Wake Word Scanner
                                wpkt.seq_num = wake_seq++;
                                wpkt.stream_flag = (wake_seq == 1) ? STREAM_FLAG_START : STREAM_FLAG_DATA;
                                memcpy(wpkt.pcm_data, wake_preroll_buf[read_idx], sizeof(wpkt.pcm_data));
                                wpkt.crc8 = calculate_crc8((const uint8_t*)&wpkt, 519);
                                wsManager.send_binary((const uint8_t*)&wpkt, sizeof(AudioPacket_t));
                                read_idx = (read_idx + 1) % WAKE_PREROLL_FRAMES;
                                vTaskDelay(pdMS_TO_TICKS(1)); // Chống nghẽn LwIP buffer
                            }
                        }
                    }
                }

                // Nếu đang stream mà có tiếng nói trong vòng 1.5s qua -> Gửi AudioPacket_t thời gian thực
                if (is_wake_streaming) {
                    if (now - last_voice_activity <= 1500) {
                        AudioPacket_t wpkt;
                        wpkt.magic = BINARY_MAGIC_WORD; // 0xA55A
                        wpkt.sender_id = my_intercom_id;
                        wpkt.target_id = 0x05; // Target 0x05: Wake Word Scanner
                        wpkt.seq_num = wake_seq++;
                        wpkt.stream_flag = STREAM_FLAG_DATA;
                        memcpy(wpkt.pcm_data, pcm_boosted, sizeof(wpkt.pcm_data));
                        wpkt.crc8 = calculate_crc8((const uint8_t*)&wpkt, 519);
                        wsManager.send_binary((const uint8_t*)&wpkt, sizeof(AudioPacket_t));
                    } else {
                        // Phòng đã yên tĩnh quá 1.5s -> Tạm dừng stream để trả băng thông về 0 KB/s
                        is_wake_streaming = false;
                    }
                }
            }
        }
    }
}

// -----------------------------------------------------------------------------
// 7. FREERTOS TASKS CHIA 2 CORE
// -----------------------------------------------------------------------------
// Task Mạng & Âm thanh I2S DMA chạy trên Core 0 (Ưu tiên mức 5)
void Task_Net_Audio(void *p) {
    while (1) {
        wsManager.loop();
        nvsStore.loop();
        handle_mic_streaming();
        // i2s_read tự động đồng bộ theo chu kỳ DMA (16ms), chỉ cần nhường CPU 1 tick
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}

// Task Giao diện đồ họa LVGL chạy trên Core 1 (Ưu tiên mức 3)
void Task_LVGL_UI(void *p) {
    while (1) {
        if (!is_ota_running) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                uiDashboard.check_flush_climate_setpoint();
                uiDashboard.tick_countdown(millis());

                // Màn hình chờ Standby: Tự động vào sau N giây không thao tác (0 = Tắt)
                // Tuyệt đối KHÔNG kích hoạt màn hình chờ khi đang trong phiên thoại AI hoặc PTT!
                uint16_t stb_sec = nvsStore.get().standby_timeout;
                bool is_voice_active = is_recording_ptt || is_hands_free_session || is_continuous_listening;
                if (stb_sec > 0 && !is_voice_active) {
                    uint32_t inactive_ms = lv_disp_get_inactive_time(NULL);
                    if (!uiDashboard.is_screensaver_active() && inactive_ms >= ((uint32_t)stb_sec * 1000)) {
                        uiDashboard.show_screensaver();
                    } else if (uiDashboard.is_screensaver_active() && inactive_ms < 500) {
                        uiDashboard.hide_screensaver();
                    }
                } else {
                    if (uiDashboard.is_screensaver_active()) {
                        uiDashboard.hide_screensaver();
                    }
                }

                // Cập nhật đồng hồ & radar telemetry mỗi giây cho Header và Screensaver
                static unsigned long last_stb_sec = 0;
                if (millis() - last_stb_sec >= 1000) {
                    last_stb_sec = millis();

                    // 1. Chuỗi Giờ & Ngày cho Header: e.g. "22:30 • 17/11" (Góc dưới bên trái: Bottom-Left)
                    String header_time_date = rtc.getTime("%H:%M • %d/%m");

                    // 2. Chuỗi Radar Telemetry: Cự ly & Trạng thái/Nhịp thở (Góc dưới bên phải: Bottom-Right)
                    const RadarStatus_t& r_stat = radarEngine.get_status();
                    char r_buf[32];
                    char light_buf[24];
                    char stb_r_buf[64];
                    uint32_t r_color = 0x64748B; // Slate gray khi phòng vắng

                    // Chuỗi độ sáng môi trường hiển thị ở góc trên bên phải (Top-Right)
                    snprintf(light_buf, sizeof(light_buf), "Sáng: %d lx", r_stat.light_level);

                    if (r_stat.has_presence) {
                        uint16_t dist = radarEngine.get_distance_cm();
                        if (r_stat.is_approaching) {
                            snprintf(r_buf, sizeof(r_buf), "%dcm • Đến gần", dist);
                            snprintf(stb_r_buf, sizeof(stb_r_buf), "Radar: %dcm • Tiến lại gần • Sáng: %d lx", dist, r_stat.light_level);
                            r_color = 0x06B6D4; // Cyan
                        } else if (r_stat.target_state == RADAR_TARGET_STATIONARY || (r_stat.static_energy > 0 && r_stat.moving_energy == 0)) {
                            snprintf(r_buf, sizeof(r_buf), "%dcm • Thở %d%%", dist, r_stat.static_energy);
                            snprintf(stb_r_buf, sizeof(stb_r_buf), "Radar: %dcm • Thở: %d%% • Sáng: %d lx", dist, r_stat.static_energy, r_stat.light_level);
                            r_color = 0x10B981; // Emerald Green (Tĩnh/Ngủ/Thở)
                        } else if (r_stat.target_state == RADAR_TARGET_MOVING) {
                            snprintf(r_buf, sizeof(r_buf), "%dcm • Động %d%%", dist, r_stat.moving_energy);
                            snprintf(stb_r_buf, sizeof(stb_r_buf), "Radar: %dcm • Động: %d%% • Sáng: %d lx", dist, r_stat.moving_energy, r_stat.light_level);
                            r_color = 0xF59E0B; // Amber (Hoạt động)
                        } else { // Combined
                            snprintf(r_buf, sizeof(r_buf), "%dcm • Thở %d%%", dist, r_stat.static_energy);
                            snprintf(stb_r_buf, sizeof(stb_r_buf), "Radar: %dcm • Thở: %d%% • Sáng: %d lx", dist, r_stat.static_energy, r_stat.light_level);
                            r_color = 0x10B981; // Green
                        }
                    } else {
                        snprintf(r_buf, sizeof(r_buf), "Phòng vắng");
                        snprintf(stb_r_buf, sizeof(stb_r_buf), "Radar: Phòng vắng • Sáng: %d lx", r_stat.light_level);
                        r_color = 0x64748B;
                    }

                    // Cập nhật Header thanh trên cùng (4 góc độc lập - không bao giờ chồng lấn)
                    uiDashboard.update_header_telemetry(header_time_date.c_str(), r_buf, r_color, light_buf);

                    // Cập nhật Standby Screensaver nếu đang kích hoạt
                    if (uiDashboard.is_screensaver_active()) {
                        String time_str = rtc.getTime("%H:%M");
                        String sec_str = rtc.getTime(":%S");
                        int wday = rtc.getDayofWeek();
                        const char* wday_names[7] = {"CHỦ NHẬT", "THỨ HAI", "THỨ BA", "THỨ TƯ", "THỨ NĂM", "THỨ SÁU", "THỨ BẢY"};
                        const char* wday_name = (wday >= 0 && wday < 7) ? wday_names[wday] : "HÔM NAY";
                        String date_str = rtc.getTime("%d/%m/%Y");
                        uiDashboard.update_standby_clock(time_str.c_str(), sec_str.c_str(), wday_name, date_str.c_str(), stb_r_buf, r_color);
                    }
                }

                lv_timer_handler();
                xSemaphoreGive(lvgl_mutex);
            }
        }
        static unsigned long last_ui_tick = 0;
        if (millis() - last_ui_tick > 3000) {
            last_ui_tick = millis();
            Serial.printf("[LVGL-TASK] Alive! Heap: %lu KB\n", (unsigned long)(ESP.getFreeHeap() / 1024));
        }
        vTaskDelay(pdMS_TO_TICKS(15));
    }
}

// Kiểm tra nút BOOT cứng (Chống treo do nạp UART)
void check_boot_button() {
    static bool button_initialized = false;
    if (!button_initialized) {
        if (digitalRead(BUTTON_BOOT_PIN) == HIGH) {
            button_initialized = true;
        }
        return;
    }

    if (digitalRead(BUTTON_BOOT_PIN) == LOW) {
        if (!boot_button_held) {
            boot_button_held = true;
            boot_button_press_time = millis();
        } else if (millis() - boot_button_press_time >= 5000) {
            boot_button_held = false;
            Serial.println("[BOOT] Phat hien giu BOOT 5s -> Factory Reset ve AP Mode!");
            nvsStore.factory_reset();
            delay(200);
            ESP.restart();
        }
    } else {
        boot_button_held = false;
    }
}

// -----------------------------------------------------------------------------
// ARDUINO SETUP
// -----------------------------------------------------------------------------
void setup() {
    // Chống nổ loa lúc boot (PA_EN = HIGH = MUTE)
    pinMode(PA_EN_PIN, OUTPUT);
    digitalWrite(PA_EN_PIN, HIGH);

    pinMode(LCD_BL_PIN, OUTPUT);
    digitalWrite(LCD_BL_PIN, HIGH);

    Serial.begin(115200);
    // Validate running partition to prevent rollback
    esp_err_t ota_val_err = esp_ota_mark_app_valid_cancel_rollback();
    Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\n", ota_val_err, esp_err_to_name(ota_val_err));
    Serial.setTxTimeoutMs(0); // Non-blocking USB CDC: khong bao gio gay treo task khi buffer day
    delay(500);
    Serial.println("\n=======================================================");
    Serial.println("  NALA SMART HOME - LVGL 8.3.11 & AI VOICE PANEL       ");
    Serial.println("=======================================================");

    // 1. Hardware Reset Touch Chip
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
    }
    pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);
    nvsStore.begin();
    lvgl_mutex = xSemaphoreCreateMutex();
    i2c_mutex = xSemaphoreCreateMutex();

    // 2. Audio Codec & LED RGB
    audioEngine.begin();
    audioEngine.set_mic_gain(nvsStore.get_mic_gain());
    audioEngine.play_beep(1200, 150); // Beep khoi dong bao hieu loa & ES8311 da san sang
    rgb_led.begin();
    rgb_led.setBrightness(40);
    rgb_led.show();

    // 3. Khởi tạo LovyanGFX
    tft.init();
    tft.setRotation(0);
    tft.setBrightness(nvsStore.get().lcd_brightness);
    tft.clear(TFT_BLACK);

    // 4. Lấy MAC & Sinh Mã Ghép Nối
    uint8_t mac[6];
    WiFi.macAddress(mac);
    char mac_str[20];
    snprintf(mac_str, sizeof(mac_str), "%02X:%02X:%02X:%02X:%02X:%02X", mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    device_mac = String(mac_str);
    char pair_str[8];
    snprintf(pair_str, sizeof(pair_str), "%02X%02X", mac[4], mac[5]);
    pairing_code = String(pair_str);
    pairing_code.toUpperCase();

    Serial.printf("[SYSTEM] MAC: %s | Ma ghep noi: %s\n", device_mac.c_str(), pairing_code.c_str());

    // 5. Kiểm tra trạng thái WiFi
    if (!nvsStore.is_wifi_configured()) {
        Serial.println("[SYSTEM] Chua co WiFi trong NVS -> Chuyen sang AP Captive Portal 192.168.4.1");
        current_state = PANEL_AP_PROVISIONING;
        captivePortal.begin(&nvsStore, pairing_code);
        draw_ap_provisioning_screen();
        rgb_led.setPixelColor(0, rgb_led.Color(255, 120, 0)); // Cam
        rgb_led.show();
    } else {
        Serial.printf("[SYSTEM] Da co WiFi: %s -> Dang ket noi...\n", nvsStore.get().wifi_ssid);
        current_state = PANEL_CONNECTING_WIFI;
        draw_connecting_screen();
        rgb_led.setPixelColor(0, rgb_led.Color(0, 0, 255)); // Xanh dương
        rgb_led.show();

        WiFi.mode(WIFI_STA);
        WiFi.begin(nvsStore.get().wifi_ssid, nvsStore.get().wifi_pass);

        uint32_t start_connect = millis();
        bool connected = false;
        while (millis() - start_connect < 12000) {
            uint16_t tx, ty;
            if (tft.getTouch(&tx, &ty)) {
                Serial.println("[TOUCH] Cham man hinh luc khoi dong -> Chuyen sang AP Mode 192.168.4.1!");
                nvsStore.factory_reset();
                delay(200);
                ESP.restart();
            }
            if (WiFi.status() == WL_CONNECTED) {
                connected = true;
                break;
            }
            delay(150);
        }

        if (connected) {
            Serial.printf("[WIFI] Ket noi thanh cong! IP: %s\n", WiFi.localIP().toString().c_str());
            current_state = PANEL_OPERATIONAL;
            rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Xanh lá
            rgb_led.show();

            // Khởi tạo LVGL 8.3.11
            lv_init();
            if (psramFound()) {
                size_t lines = 80;
                buf1 = (lv_color_t*) ps_malloc(LCD_WIDTH * lines * sizeof(lv_color_t));
                buf2 = (lv_color_t*) ps_malloc(LCD_WIDTH * lines * sizeof(lv_color_t));
                if (buf1 && buf2) {
                    lv_disp_draw_buf_init(&draw_buf, buf1, buf2, LCD_WIDTH * lines);
                    Serial.printf("[LVGL-PSRAM] Initialized Double Buffering in PSRAM (2x %u lines, %u KB)\n",
                                  (unsigned int)lines, (unsigned int)(2 * LCD_WIDTH * lines * sizeof(lv_color_t) / 1024));
                }
                // Pre-Roll Ring Buffer cho Wake Word ranh tay trong 8MB PSRAM
                wake_preroll_buf = (int16_t(*)[AUDIO_FRAME_SAMPLES]) ps_malloc(WAKE_PREROLL_FRAMES * sizeof(int16_t) * AUDIO_FRAME_SAMPLES);
                if (wake_preroll_buf) {
                    memset(wake_preroll_buf, 0, WAKE_PREROLL_FRAMES * sizeof(int16_t) * AUDIO_FRAME_SAMPLES);
                    Serial.printf("[WAKE-PSRAM] Initialized Pre-Roll Buffer (%d frames, %d KB)\n",
                                  WAKE_PREROLL_FRAMES, (int)(WAKE_PREROLL_FRAMES * sizeof(int16_t) * AUDIO_FRAME_SAMPLES / 1024));
                }
            }
            if (!buf1 || !buf2) {
                lv_disp_draw_buf_init(&draw_buf, buf_fallback, NULL, LCD_WIDTH * 20);
                Serial.println("[LVGL] Using fallback internal SRAM single buffer");
            }

            lv_disp_drv_init(&disp_drv);
            disp_drv.hor_res = LCD_WIDTH;
            disp_drv.ver_res = LCD_HEIGHT;
            disp_drv.flush_cb = my_disp_flush;
            disp_drv.draw_buf = &draw_buf;
            lv_disp_drv_register(&disp_drv);

            lv_indev_drv_init(&indev_drv);
            indev_drv.type = LV_INDEV_TYPE_POINTER;
            indev_drv.read_cb = my_touchpad_read;
            indev_drv.scroll_limit = 35;
            lv_indev_drv_register(&indev_drv);

            // Xây dựng giao diện Dashboard
            uiDashboard.set_action_callback(on_ui_action);
            uiDashboard.init(
                nvsStore.get().room_name,
                WiFi.localIP().toString().c_str(),
                pairing_code.c_str(),
                nvsStore.get().speaker_volume,
                nvsStore.get().lcd_brightness,
                nvsStore.get().ring_on_call,
                nvsStore.get_mic_gain()
            );
            uiDashboard.set_room_view_timeout(nvsStore.get().room_view_timeout);
            float psram_mb = psramFound() ? ((float)ESP.getFreePsram() / (1024.0f * 1024.0f)) : 0.0f;
            uiDashboard.set_firmware_version(CURRENT_FIRMWARE_VERSION, psram_mb);
            Serial.printf("[SYSTEM] Firmware %s | PSRAM: %.2f MB free | Heap: %lu KB free\n", 
                          CURRENT_FIRMWARE_VERSION, psram_mb, (unsigned long)(ESP.getFreeHeap() / 1024));

            // Mở kết nối WebSocket
            wsManager.set_callbacks(on_ws_text, on_ws_binary, on_ws_connected, on_ws_disconnected);
            wsManager.begin(nvsStore.get().nas_ws_url);

            // Khởi tạo Radar mmWave HLK-LD2410C (UART1: RX GPIO 21, TX GPIO 14)
            radarEngine.begin();

            // Khởi chạy 2 FreeRTOS Tasks trên 2 Core
            xTaskCreatePinnedToCore(Task_Net_Audio, "NetAudio", 16384, NULL, 5, NULL, 0);
            xTaskCreatePinnedToCore(Task_LVGL_UI, "LVGL_UI", 12288, NULL, 3, NULL, 1);
        } else {
            Serial.println("[WIFI] Ket noi that bai -> Bat AP Captive Portal 192.168.4.1");
            current_state = PANEL_AP_PROVISIONING;
            captivePortal.begin(&nvsStore, pairing_code);
            draw_ap_provisioning_screen();
            rgb_led.setPixelColor(0, rgb_led.Color(255, 0, 0)); // Đỏ
            rgb_led.show();
        }
    }
}

// -----------------------------------------------------------------------------
// ARDUINO LOOP
// -----------------------------------------------------------------------------
void loop() {
    check_boot_button();

    if (Serial.available()) {
        char ch = Serial.read();
        if (ch == 't') {
            Serial.println("[CMD] Trigger TEST LOA 1kHz...");
            run_speaker_test();
        } else if (ch == 'm') {
            Serial.println("[CMD] Trigger TEST MIC...");
            run_mic_test();
        } else if (ch == 's') {
            Serial.println("[CMD] Dump 32 I2S samples (L vs R):");
            audioEngine.enable_mic(true);
            int16_t buf[64 * 2];
            size_t br = 0;
            i2s_read(I2S_NUM_0, buf, sizeof(buf), &br, 100);
            for (int i = 0; i < 32; i++) {
                Serial.printf("[%2d] L=%6d | R=%6d\n", i, buf[i*2], buf[i*2+1]);
            }
        } else if (ch == 'd') {
            audioEngine.dump_registers();
        } else if (ch == '0') {
            Serial.println("[CMD] PA_EN = LOW (Bật Amply)");
            pinMode(PA_EN_PIN, OUTPUT);
            digitalWrite(PA_EN_PIN, LOW);
        } else if (ch == '1') {
            Serial.println("[CMD] PA_EN = HIGH (Tắt Amply)");
            pinMode(PA_EN_PIN, OUTPUT);
            digitalWrite(PA_EN_PIN, HIGH);
        } else if (ch == 'i') {
            scan_i2c_bus();
        } else if (ch == 'c') {
            set_touch_calib_mode(global_touch_mode + 1);
        } else if (ch >= '2' && ch <= '7') {
            set_touch_calib_mode(ch - '0');
        } else if (ch == 'w') {
            Serial.println("[CMD] Live Touch Monitor for 5s... Touch screen NOW!");
            unsigned long t_end = millis() + 5000;
            while (millis() < t_end) {
                int16_t x = 0, y = 0;
                bool t = read_touch_calibrated(&x, &y);
                if (t) {
                    Serial.printf("  TOUCH DETECTED -> (%d, %d)\n", x, y);
                }
                delay(50);
            }
            Serial.println("[CMD] Live Touch Monitor ended.");
        } else if (ch == 'p') {
            Serial.println("[CMD] Probing FT6336 registers & Pins:");
            Serial.printf("  TOUCH_INT_PIN (GPIO 17) = %d\n", digitalRead(TOUCH_INT_PIN));
            Serial.printf("  TOUCH_RST_PIN (GPIO 18) = %d\n", digitalRead(TOUCH_RST_PIN));
            Wire.beginTransmission(0x38);
            Wire.write(0x00);
            uint8_t err = Wire.endTransmission(false);
            Serial.printf("  endTransmission(false) err=%d\n", err);
            uint8_t n = Wire.requestFrom((uint16_t)0x38, (uint8_t)16, true);
            Serial.printf("  requestFrom(0x00, 16) -> %d bytes:\n", n);
            for (uint8_t i = 0; i < n; i++) {
                uint8_t b = Wire.read();
                Serial.printf("    Reg 0x%02X = 0x%02X (%d)\n", i, b, b);
            }
            Wire.beginTransmission(0x38);
            Wire.write(0x02);
            err = Wire.endTransmission(true);
            n = Wire.requestFrom((uint16_t)0x38, (uint8_t)6, true);
            Serial.printf("  write(0x02) + stop err=%d -> %d bytes:\n", err, n);
            for (uint8_t i = 0; i < n; i++) {
                uint8_t b = Wire.read();
                Serial.printf("    Byte %d = 0x%02X\n", i, b);
            }
        } else if (ch == 'r') {
            const RadarStatus_t& st = radarEngine.get_status();
            Serial.printf("[RADAR STATUS] Presence: %s | State: %u | Dist: %u cm | MvEng: %u | StEng: %u | Approach: %s\n",
                          st.has_presence ? "YES" : "NO",
                          st.target_state,
                          st.detect_distance_cm,
                          st.moving_energy,
                          st.static_energy,
                          st.is_approaching ? "YES" : "NO");
        }
    }

    if (current_state == PANEL_AP_PROVISIONING) {
        captivePortal.loop();
        delay(10);
        return;
    }

    // -------------------------------------------------------------------------
    // RADAR HLK-LD2410C MMWAVE ENGINE (UART1: RX GPIO 21, TX GPIO 14)
    // -------------------------------------------------------------------------
    if (nvsStore.get().radar_enabled) {
        radarEngine.loop();

        // 1. Radar Touchless HMI: Đánh thức màn hình khi phát hiện người tiếp cận/đứng gần theo cấu hình
        uint16_t wake_dist = nvsStore.get().radar_wake_dist;
        if (wake_dist == 0) wake_dist = 150;
        uint16_t target_dist = radarEngine.get_distance_cm();

        // Đánh thức nếu: Có người và khoảng cách mục tiêu <= wake_dist (HOẶC đang tiếp cận trong phạm vi wake_dist + 30cm)
        bool should_wake = radarEngine.has_presence() && (
            (target_dist > 0 && target_dist <= wake_dist) ||
            (radarEngine.is_approaching() && target_dist > 0 && target_dist <= (wake_dist + 30))
        );

        if (should_wake) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                if (uiDashboard.is_screensaver_active()) {
                    Serial.printf("[RADAR-WAKE] Phat hien nguoi toi gan (cur=%u cm, wake_dist=%u cm) -> Danh thuc man hinh!\n",
                                  target_dist, wake_dist);
                    uiDashboard.hide_screensaver();
                    tft.setBrightness(nvsStore.get().lcd_brightness);
                }
                lv_disp_trig_activity(NULL); // Reset bộ đếm thời gian không hoạt động của LVGL
                xSemaphoreGive(lvgl_mutex);
            }
        }

        // 2. Radar Hand-Wave Gesture: Vẫy tay trước mặt màn hình (< 30cm) để cúp máy Intercom
        if (nvsStore.get().radar_wave_hangup && radarEngine.check_and_clear_wave_gesture()) {
            if (is_intercom_call_active) {
                Serial.println("[RADAR] Phat hien cu chi gat tay -> Tu dong cup may dam thoai Intercom!");
                on_ui_action("intercom_hangup", "hangup", 0);
            }
        }

        // 3. Truyền Telemetry Radar & Ánh sáng môi trường lên NAS Hub mỗi 2 giây
        static unsigned long last_radar_telemetry_tx = 0;
        if (millis() - last_radar_telemetry_tx >= 2000) {
            last_radar_telemetry_tx = millis();
            if (wsManager.is_connected()) {
                const RadarStatus_t& r_stat = radarEngine.get_status();
                JsonDocument r_doc;
                r_doc["type"] = "radar_event";
                r_doc["source"] = device_mac;
                r_doc["payload"]["presence"] = r_stat.has_presence;
                r_doc["payload"]["dist_cm"] = radarEngine.get_distance_cm();
                r_doc["payload"]["state"] = (uint8_t)r_stat.target_state;
                r_doc["payload"]["st_eng"] = r_stat.static_energy;
                r_doc["payload"]["mv_eng"] = r_stat.moving_energy;
                r_doc["payload"]["light"] = r_stat.light_level;
                r_doc["payload"]["is_approaching"] = r_stat.is_approaching;
                String r_out;
                serializeJson(r_doc, r_out);
                wsManager.send_text(r_out);
            }
        }
    }

    // Giảm độ trễ từ 50ms xuống 10ms để tránh tràn FIFO UART 256,000 baud
    vTaskDelay(pdMS_TO_TICKS(10));
}
