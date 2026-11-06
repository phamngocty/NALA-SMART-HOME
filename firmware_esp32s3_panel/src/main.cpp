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
SemaphoreHandle_t lvgl_mutex = NULL;
SemaphoreHandle_t i2c_mutex = NULL;

#include "ota_manager.h"
#include "esp_ota_ops.h"
volatile bool is_ota_running = false;
#define CURRENT_FIRMWARE_VERSION "v3.3.1"

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
static volatile uint8_t ptt_target_id = TARGET_ID_AI_SERVER;
static volatile bool ptt_start_flag = false;
static volatile uint8_t my_intercom_id = 0x01; // Dynamic Intercom ID from NAS Hub

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
static lv_color_t buf1[LCD_WIDTH * 40];
static lv_color_t buf2[LCD_WIDTH * 40];
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
            audioEngine.mute_speaker(true); // Half-duplex
            audioEngine.enable_mic(true);
            rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương
            rgb_led.show();
            Serial.println("[AI PTT] Start recording...");
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
    String out;
    serializeJson(doc, out);
    wsManager.send_text(out);
    Serial.println("[WS] Da gui goi tin dang ky thiet bi len NAS Hub!");
}

void on_ws_connected() {
    send_device_registration();
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

    Serial.printf("[WS-TEXT] Handling type: %s, FreeHeap: %lu\n", type.c_str(), (unsigned long)ESP.getFreeHeap());
    if (type == "ai_state") {
        String state = doc["payload"]["state"] | "IDLE";
        String txt = doc["payload"]["text"] | "";
        if (taken) uiDashboard.set_ai_state(state.c_str(), txt.c_str());
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

            if (p->stream_flag == STREAM_FLAG_START) {
                char caller_buf[64];
                uiDashboard.get_caller_display(p->sender_id, caller_buf, sizeof(caller_buf));
                bool ring = nvsStore.get().ring_on_call;

                bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                if (taken) {
                    uiDashboard.show_incoming_call(caller_buf, ring);
                    uiDashboard.set_intercom_status("Cuộc gọi đến...", 0xF59E0B);
                    xSemaphoreGive(lvgl_mutex);
                }

                rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương
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

            if (p->stream_flag == STREAM_FLAG_END) {
                delay(200); // Đợi 200ms để DMA phát hết trọn vẹn từ cuối câu trước khi ngắt amply
                audioEngine.mute_speaker(true);
                rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Trở lại xanh lá
                rgb_led.show();

                bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                if (taken) {
                    uiDashboard.hide_incoming_call();
                    uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                    xSemaphoreGive(lvgl_mutex);
                }
                Serial.println("[INTERCOM] Kết thúc cuộc gọi.");
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

            pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
            wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
        }
    } else if (was_recording) {
        // Gửi gói tin cờ kết thúc (STREAM_FLAG_END = 0x03) để Server xử lý STT / AI tức thì
        was_recording = false;
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
        // Khi thu âm PTT, giảm delay để i2s_read tự đồng bộ thời gian thực mượt mà
        if (is_recording_ptt) {
            vTaskDelay(pdMS_TO_TICKS(1));
        } else {
            vTaskDelay(pdMS_TO_TICKS(5));
        }
    }
}

// Task Giao diện đồ họa LVGL chạy trên Core 1 (Ưu tiên mức 3)
void Task_LVGL_UI(void *p) {
    while (1) {
        if (!is_ota_running) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
                uiDashboard.check_flush_climate_setpoint();
                uiDashboard.tick_countdown(millis());
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
            lv_disp_draw_buf_init(&draw_buf, buf1, buf2, LCD_WIDTH * 40);

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

            // Khởi chạy 2 FreeRTOS Tasks trên 2 Core
            xTaskCreatePinnedToCore(Task_Net_Audio, "NetAudio", 12288, NULL, 5, NULL, 0);
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
        }
    }

    if (current_state == PANEL_AP_PROVISIONING) {
        captivePortal.loop();
        delay(10);
        return;
    }

    // Các tác vụ chính đã chạy trong FreeRTOS Tasks trên Core 0 và Core 1
    delay(50);
}
