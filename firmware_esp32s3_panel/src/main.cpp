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
            cfg.invert           = false;
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

#include "ota_manager.h"
volatile bool is_ota_running = false;

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

// Đọc tọa độ cảm ứng điện dung FT6336G đảo 180° chuẩn xác
bool read_touch_calibrated(int16_t *x, int16_t *y) {
    Wire.beginTransmission(I2C_ADDR_FT6336U);
    Wire.write(0x02);
    if (Wire.endTransmission() != 0) return false;

    if (Wire.requestFrom((int)I2C_ADDR_FT6336U, 5) == 5) {
        uint8_t points = Wire.read() & 0x0F;
        if (points > 0) {
            uint8_t x_high = Wire.read();
            uint8_t x_low  = Wire.read();
            uint8_t y_high = Wire.read();
            uint8_t y_low  = Wire.read();
            int16_t raw_x = ((x_high & 0x0F) << 8) | x_low;
            int16_t raw_y = ((y_high & 0x0F) << 8) | y_low;

            *x = constrain((LCD_WIDTH - 1) - raw_x, 0, LCD_WIDTH - 1);
            *y = constrain((LCD_HEIGHT - 1) - raw_y, 0, LCD_HEIGHT - 1);
            return true;
        }
    }
    return false;
}

void my_touchpad_read(lv_indev_drv_t *indev_driver, lv_indev_data_t *data) {
    int16_t x = 0, y = 0;
    if (read_touch_calibrated(&x, &y)) {
        data->state = LV_INDEV_STATE_PR;
        data->point.x = x;
        data->point.y = y;
    } else {
        data->state = LV_INDEV_STATE_REL;
    }
}

// -----------------------------------------------------------------------------
// 3. UI ACTION CALLBACKS (TƯƠNG TÁC GIAO DIỆN LVGL)
// -----------------------------------------------------------------------------
static unsigned long ws_ping_start_ms = 0;

void run_speaker_test() {
    Serial.println("[DIAG] Bắt đầu test Loa 1kHz...");
    audioEngine.mute_speaker(false);
    audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);

    int16_t sample_buffer[256];
    for (int i = 0; i < 256; i++) {
        float angle = 2.0f * 3.14159265f * (float)(i % 16) / 16.0f;
        sample_buffer[i] = (int16_t)(sin(angle) * 12000.0f);
    }

    size_t bytes_written = 0;
    for (int c = 0; c < 75; c++) {
        i2s_write(I2S_NUM_0, sample_buffer, sizeof(sample_buffer), &bytes_written, portMAX_DELAY);
    }
    uiDashboard.set_diag_result("Loa: Kiểm tra OK (1kHz)!", 0x10B981);
    Serial.println("[DIAG] Test Loa thành công!");
}

void run_mic_test() {
    Serial.println("[DIAG] Bắt đầu test Mic...");
    uiDashboard.set_diag_result("Mic: Đang thu 1.5s (Hãy nói)...", 0x3B82F6);
    rgb_led.setPixelColor(0, rgb_led.Color(255, 100, 0));
    rgb_led.show();

    const size_t total_samples = 24000;
    int16_t* mic_buf = (int16_t*)ps_malloc(total_samples * sizeof(int16_t));
    if (!mic_buf) {
        uiDashboard.set_diag_result("Mic: Không đủ RAM PSRAM!", 0xEF4444);
        return;
    }

    size_t bytes_read = 0;
    i2s_read(I2S_NUM_0, mic_buf, total_samples * sizeof(int16_t), &bytes_read, portMAX_DELAY);

    size_t samples_read = bytes_read / sizeof(int16_t);
    int64_t sum_sq = 0;
    for (size_t i = 0; i < samples_read; i++) {
        sum_sq += ((int32_t)mic_buf[i] * mic_buf[i]);
    }
    int rms = (samples_read > 0) ? (int)sqrt(sum_sq / samples_read) : 0;
    Serial.printf("[DIAG] Mic thu %d mẫu, RMS = %d\n", samples_read, rms);

    uiDashboard.set_diag_result("Mic: Đang phát lại qua loa...", 0xF59E0B);
    rgb_led.setPixelColor(0, rgb_led.Color(0, 150, 255));
    rgb_led.show();

    audioEngine.mute_speaker(false);
    size_t bytes_written = 0;
    i2s_write(I2S_NUM_0, mic_buf, bytes_read, &bytes_written, portMAX_DELAY);
    free(mic_buf);

    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
    rgb_led.show();

    char res_str[64];
    snprintf(res_str, sizeof(res_str), "Mic: Tốt (RMS: %d, Đã phát lại)!", rms);
    uiDashboard.set_diag_result(res_str, 0x10B981);
    Serial.println("[DIAG] Test Mic hoàn thành!");
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
    } else if (strcmp(target, "diag_speaker") == 0) {
        run_speaker_test();
    } else if (strcmp(target, "diag_mic") == 0) {
        run_mic_test();
    } else if (strcmp(target, "diag_ws") == 0) {
        run_ws_ping_test();
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
            ptt_target_id = (value == 0xFF) ? 0xFF : (uint8_t)value;
            ptt_start_flag = true;
            is_recording_ptt = true;
            audioEngine.mute_speaker(true);
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
    } else if (strcmp(target, "volume") == 0) {
        nvsStore.get().speaker_volume = value;
        audioEngine.set_speaker_volume(value);
        nvsStore.save_immediate();
    } else if (strcmp(target, "brightness") == 0) {
        nvsStore.get().lcd_brightness = value;
        tft.setBrightness(value);
        nvsStore.save_immediate();
    } else if (strcmp(target, "ai_model") == 0) {
        strncpy(nvsStore.get().ai_model, action, sizeof(nvsStore.get().ai_model));
        nvsStore.save_immediate();
    } else if (strcmp(target, "system") == 0 && strcmp(action, "enter_ap_mode") == 0) {
        Serial.println("[SYSTEM] Nguoi dung yeu cau vao Che Do Cau Hinh Soft-AP!");
        nvsStore.factory_reset();
        delay(250);
        ESP.restart();
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
void send_device_registration() {
    JsonDocument doc;
    doc["type"] = "register";
    doc["payload"]["mac"] = device_mac;
    doc["payload"]["pairing_code"] = pairing_code;
    doc["payload"]["ip"] = WiFi.localIP().toString();
    doc["payload"]["model"] = "ES3C28P";
    doc["payload"]["room"] = nvsStore.get().room_name;
    String out;
    serializeJson(doc, out);
    wsManager.send_text(out);
    Serial.println("[WS] Da gui goi tin dang ky thiet bi len NAS Hub!");
}

void on_ws_connected() {
    send_device_registration();
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

    if (lvgl_mutex != NULL) xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(150));

    if (type == "ai_state") {
        String state = doc["payload"]["state"] | "IDLE";
        String txt = doc["payload"]["text"] | "";
        uiDashboard.set_ai_state(state.c_str(), txt.c_str());
    } else if (type == "config_sync") {
        uint8_t assigned_id = doc["payload"]["my_intercom_id"] | 0;
        if (assigned_id > 0) {
            my_intercom_id = assigned_id;
            Serial.printf("[INTERCOM] Assigned My Intercom ID: 0x%02X (%d)\n", my_intercom_id, my_intercom_id);
        }
        JsonArrayConst targets = doc["payload"]["intercom_targets"];
        if (targets.size() > 0) {
            uiDashboard.sync_intercom_targets(targets);
        }

        String new_room = doc["payload"]["room"] | "";
        if (new_room.length() > 0) {
            strncpy(nvsStore.get().room_name, new_room.c_str(), sizeof(nvsStore.get().room_name));
            nvsStore.save_immediate();
            Serial.printf("[SYNC] Da dong bo ten phong moi: %s\n", new_room.c_str());
            uiDashboard.set_room_title(new_room.c_str());
        }

        JsonArrayConst buttons = doc["payload"]["buttons"];
        if (buttons.size() > 0) {
            uiDashboard.sync_buttons(buttons);
        }
    } else if (type == "intercom_sync") {
        uint8_t assigned_id = doc["payload"]["my_intercom_id"] | 0;
        if (assigned_id > 0) my_intercom_id = assigned_id;
        JsonArrayConst targets = doc["payload"]["targets"];
        uiDashboard.sync_intercom_targets(targets);
    } else if (type == "ha_state_change") {
        String entity_id = doc["payload"]["entity_id"] | "";
        String state = doc["payload"]["state"] | "";
        bool is_on = (state == "on" || (state != "off" && state != "unavailable"));
        uiDashboard.update_entity_state(entity_id.c_str(), is_on);
    } else if (type == "pong") {
        unsigned long now = millis();
        unsigned long client_time = doc["client_time"] | ws_ping_start_ms;
        unsigned long rtt = (now >= client_time) ? (now - client_time) : 0;
        char buf[64];
        snprintf(buf, sizeof(buf), "Server: Kết nối OK (%lu ms)", rtt);
        uiDashboard.set_diag_result(buf, 0x10B981);
        Serial.printf("[DIAG] Pong received: RTT = %lu ms\n", rtt);
    }

    if (lvgl_mutex != NULL) xSemaphoreGive(lvgl_mutex);
}

// Nhận Audio Binary 520 Byte từ Server NAS phát ra Loa
void on_ws_binary(const uint8_t* data, size_t len) {
    if (len == BINARY_PACKET_SIZE) {
        const AudioPacket_t* p = (const AudioPacket_t*)data;
        if (p->magic == BINARY_MAGIC_WORD) {
            // Half-duplex: Neu dang giu nut noi thi khong phat de chong feedback
            if (is_recording_ptt) return;

            if (p->stream_flag == STREAM_FLAG_START) {
                rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh duong
                rgb_led.show();
                uiDashboard.set_intercom_status("Dang nghe dam thoai...", 0x3B82F6);
            }

            size_t written = 0;
            i2s_write(I2S_NUM_0, p->pcm_data, sizeof(p->pcm_data), &written, portMAX_DELAY);

            if (p->stream_flag == STREAM_FLAG_END) {
                rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Tro lai xanh la
                rgb_led.show();
                uiDashboard.set_intercom_status("Dam thoai: San sang", 0x10B981);
            }
        }
    }
}

// -----------------------------------------------------------------------------
// 6. THU ÂM I2S DMA STREAMING (CORE 0)
// -----------------------------------------------------------------------------
void handle_mic_streaming() {
    static uint16_t seq = 0;
    static int16_t mic_buf[AUDIO_FRAME_SAMPLES];
    static bool was_recording = false;
    size_t bytes_read = 0;

    if (is_recording_ptt) {
        was_recording = true;
        esp_err_t res = i2s_read(I2S_NUM_0, mic_buf, sizeof(mic_buf), &bytes_read, pdMS_TO_TICKS(16));
        if (res == ESP_OK && bytes_read == sizeof(mic_buf)) {
            AudioPacket_t pkt;
            pkt.magic = BINARY_MAGIC_WORD;
            pkt.sender_id = my_intercom_id; // Dynamic Intercom ID
            pkt.target_id = ptt_target_id;
            pkt.seq_num = seq++;
            pkt.stream_flag = ptt_start_flag ? STREAM_FLAG_START : STREAM_FLAG_DATA;
            ptt_start_flag = false;
            memcpy(pkt.pcm_data, mic_buf, sizeof(mic_buf));
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
        vTaskDelay(pdMS_TO_TICKS(5));
    }
}

// Task Giao diện đồ họa LVGL chạy trên Core 1 (Ưu tiên mức 3)
void Task_LVGL_UI(void *p) {
    while (1) {
        if (!is_ota_running) {
            if (lvgl_mutex != NULL && xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(40)) == pdTRUE) {
                lv_timer_handler();
                xSemaphoreGive(lvgl_mutex);
            }
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
    delay(500);
    Serial.println("\n=======================================================");
    Serial.println("  NALA SMART HOME - LVGL 8.3.11 & AI VOICE PANEL       ");
    Serial.println("=======================================================");

    // 1. Hardware Reset FT6336G
    pinMode(TOUCH_RST_PIN, OUTPUT);
    digitalWrite(TOUCH_RST_PIN, LOW);
    delay(20);
    digitalWrite(TOUCH_RST_PIN, HIGH);
    delay(50);

    Wire.begin(I2C_PORT_SDA_PIN, I2C_PORT_SCL_PIN, I2C_BUS_FREQ_HZ);
    pinMode(BUTTON_BOOT_PIN, INPUT_PULLUP);
    nvsStore.begin();
    lvgl_mutex = xSemaphoreCreateMutex();

    // 2. Audio Codec & LED RGB
    audioEngine.begin();
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
            lv_indev_drv_register(&indev_drv);

            // Xây dựng giao diện Dashboard
            uiDashboard.set_action_callback(on_ui_action);
            uiDashboard.init(
                nvsStore.get().room_name,
                WiFi.localIP().toString().c_str(),
                pairing_code.c_str(),
                nvsStore.get().speaker_volume,
                nvsStore.get().lcd_brightness
            );

            // Mở kết nối WebSocket
            wsManager.set_callbacks(on_ws_text, on_ws_binary, on_ws_connected);
            wsManager.begin(nvsStore.get().nas_ws_url);

            // Khởi chạy 2 FreeRTOS Tasks trên 2 Core
            xTaskCreatePinnedToCore(Task_Net_Audio, "NetAudio", 8192, NULL, 5, NULL, 0);
            xTaskCreatePinnedToCore(Task_LVGL_UI, "LVGL_UI", 8192, NULL, 3, NULL, 1);
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

    if (current_state == PANEL_AP_PROVISIONING) {
        captivePortal.loop();
        delay(10);
        return;
    }

    // Các tác vụ chính đã chạy trong FreeRTOS Tasks trên Core 0 và Core 1
    delay(50);
}
