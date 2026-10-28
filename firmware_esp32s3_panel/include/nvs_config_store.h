#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - NVS CONFIGURATION STORE
 * Handles WiFi SSID/Password, Room Name, NAS IP/Port, Volume, Brightness
 * Debounce 5s before saving, Hold BOOT 3s at startup to Factory Reset
 * ==============================================================================
 */

#include <Arduino.h>
#include <Preferences.h>

struct SystemConfig_t {
    char wifi_ssid[64];
    char wifi_pass[64];
    char nas_ws_url[128]; // e.g. "ws://192.168.1.114:8765/ws/panel_tang_1"
    char room_name[96];   // Cho phép tên tiếng Việt có dấu dài không bị cắt đứt UTF-8
    uint8_t speaker_volume;
    uint8_t lcd_brightness;
    uint8_t mic_gain_db;
    char ai_model[16];    // "gemini" or "deepseek"
};

class NVSConfigStore {
private:
    Preferences prefs;
    SystemConfig_t config;
    bool dirty;
    uint32_t last_change_time;

public:
    NVSConfigStore() : dirty(false), last_change_time(0) {}

    void begin() {
        prefs.begin("nala_cfg", false);
        load();
    }

    void load() {
        if (prefs.isKey("ssid")) {
            prefs.getString("ssid", config.wifi_ssid, sizeof(config.wifi_ssid));
        } else {
            config.wifi_ssid[0] = '\0'; // Chưa cấu hình WiFi
        }

        prefs.getString("pass", config.wifi_pass, sizeof(config.wifi_pass));
        prefs.getString("ws_url", config.nas_ws_url, sizeof(config.nas_ws_url));
        if (strlen(config.nas_ws_url) == 0) strcpy(config.nas_ws_url, "ws://192.168.1.114:8765/ws");

        prefs.getString("room", config.room_name, sizeof(config.room_name));
        config.room_name[sizeof(config.room_name) - 1] = '\0';

        // Kiểm tra tính hợp lệ của chuỗi UTF-8 room_name
        bool valid_utf8 = true;
        const unsigned char* bytes = (const unsigned char*)config.room_name;
        int len = strlen(config.room_name);
        for (int i = 0; i < len; ) {
            if (bytes[i] <= 0x7F) { i += 1; }
            else if ((bytes[i] & 0xE0) == 0xC0) {
                if (i + 1 >= len || (bytes[i+1] & 0xC0) != 0x80) { valid_utf8 = false; break; }
                i += 2;
            } else if ((bytes[i] & 0xF0) == 0xE0) {
                if (i + 2 >= len || (bytes[i+1] & 0xC0) != 0x80 || (bytes[i+2] & 0xC0) != 0x80) { valid_utf8 = false; break; }
                i += 3;
            } else { valid_utf8 = false; break; }
        }
        if (!valid_utf8 || len == 0) {
            strcpy(config.room_name, "Phong Khach");
        }

        config.speaker_volume = prefs.getUChar("vol", 80);
        config.lcd_brightness = prefs.getUChar("bright", 200);
        config.mic_gain_db = prefs.getUChar("mic_gain", 12);

        prefs.getString("ai_model", config.ai_model, sizeof(config.ai_model));
        if (strlen(config.ai_model) == 0) strcpy(config.ai_model, "gemini");
    }

    bool is_wifi_configured() const {
        return (strlen(config.wifi_ssid) > 0);
    }

    void save_immediate() {
        save();
    }

    void save() {
        prefs.putString("ssid", config.wifi_ssid);
        prefs.putString("pass", config.wifi_pass);
        prefs.putString("ws_url", config.nas_ws_url);
        prefs.putString("room", config.room_name);
        prefs.putUChar("vol", config.speaker_volume);
        prefs.putUChar("bright", config.lcd_brightness);
        prefs.putUChar("mic_gain", config.mic_gain_db);
        prefs.putString("ai_model", config.ai_model);
        dirty = false;
        Serial.println("[NVS] Configuration saved to Flash!");
    }

    void factory_reset() {
        prefs.clear();
        Serial.println("[NVS] FACTORY RESET: All settings cleared!");
        load();
    }

    SystemConfig_t& get() { return config; }

    void mark_dirty() {
        dirty = true;
        last_change_time = millis();
    }

    void loop() {
        // Debounce 5s: Lưu vào Flash sau khi người dùng ngừng chỉnh sửa 5s
        if (dirty && (millis() - last_change_time >= 5000)) {
            save();
        }
    }
};

extern NVSConfigStore nvsStore;
