#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - HLK-LD2410C MMWAVE RADAR ENGINE
 * Protocol: Hi-Link 24GHz FMCW Human Presence Radar
 * UART1: RX Pin 21 (from Radar TX), TX Pin 14 (to Radar RX) at 256,000 bps
 * Zero-RAM Architecture: Static ringbuffer, zero heap fragmentation.
 * ==============================================================================
 */

#include <Arduino.h>
#include "pins_config.h"
#include "ws_client_manager.h"

#define RADAR_HEADER_0          0xF4
#define RADAR_HEADER_1          0xF3
#define RADAR_HEADER_2          0xF2
#define RADAR_HEADER_3          0xF1

#define RADAR_TAIL_0            0xF8
#define RADAR_TAIL_1            0xF7
#define RADAR_TAIL_2            0xF6
#define RADAR_TAIL_3            0xF5

// Trạng thái mục tiêu chuẩn hóa
enum RadarTargetState {
    RADAR_TARGET_NONE        = 0x00,
    RADAR_TARGET_MOVING      = 0x01,
    RADAR_TARGET_STATIONARY  = 0x02,
    RADAR_TARGET_COMBINED    = 0x03
};

typedef struct {
    uint8_t  target_state;       // 0: None, 1: Moving, 2: Stationary, 3: Combined
    uint16_t moving_distance_cm; // Cự ly mục tiêu chuyển động (cm)
    uint8_t  moving_energy;      // Năng lượng chuyển động (0 - 100)
    uint16_t static_distance_cm; // Cự ly mục tiêu tĩnh / nhịp thở (cm)
    uint8_t  static_energy;      // Năng lượng tĩnh (0 - 100)
    uint16_t detect_distance_cm; // Cự ly mục tiêu gần nhất (cm)
    bool     has_presence;       // True nếu có người trong phòng
    bool     is_approaching;     // True nếu mục tiêu đang tiến lại gần panel
    uint8_t  light_level;        // Cường độ ánh sáng môi trường từ quang trở LD2410 (0 - 255)
} RadarStatus_t;

class RadarLD2410Engine {
private:
    HardwareSerial radarSerial;
    uint8_t rx_buffer[128];
    uint8_t rx_idx;
    RadarStatus_t status;
    uint16_t last_sync_distance;
    bool last_sync_presence;
    uint8_t last_sync_light;
    uint16_t last_approach_distance;
    unsigned long last_ws_sync_ms;
    unsigned long wave_gesture_start_ms;
    bool wave_gesture_detected;
    bool is_initialized;

public:
    RadarLD2410Engine() : radarSerial(RADAR_UART_NUM), rx_idx(0),
                          last_sync_distance(0), last_sync_presence(false), last_sync_light(0),
                          last_approach_distance(0), last_ws_sync_ms(0),
                          wave_gesture_start_ms(0), wave_gesture_detected(false),
                          is_initialized(false) {
        memset(&status, 0, sizeof(RadarStatus_t));
    }

    void begin() {
        pinMode(RADAR_OUT_PIN, INPUT);
        radarSerial.begin(RADAR_BAUD_RATE, SERIAL_8N1, RADAR_RX_PIN, RADAR_TX_PIN);
        is_initialized = true;
        Serial.printf("[RADAR] Initialized HLK-LD2410C on UART%d (RX: GPIO %d, TX: GPIO %d, OUT: GPIO %d) @ %d bps\n",
                      RADAR_UART_NUM, RADAR_RX_PIN, RADAR_TX_PIN, RADAR_OUT_PIN, RADAR_BAUD_RATE);
        enable_engineering_mode();
    }

    // Kích hoạt Engineering Mode để nhận dữ liệu cảm biến ánh sáng (Byte 37)
    void enable_engineering_mode() {
        if (!is_initialized) return;
        // 1. Vào chế độ Config (0x00FF)
        const uint8_t cmd_enter[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x04, 0x00, 0xFF, 0x00, 0x01, 0x00, 0x04, 0x03, 0x02, 0x01};
        radarSerial.write(cmd_enter, sizeof(cmd_enter));
        radarSerial.flush();
        delay(50);

        // 2. Bật Engineering Mode (0x0062)
        const uint8_t cmd_eng[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x02, 0x00, 0x62, 0x00, 0x04, 0x03, 0x02, 0x01};
        radarSerial.write(cmd_eng, sizeof(cmd_eng));
        radarSerial.flush();
        delay(50);

        // 3. Thoát chế độ Config (0x00FE)
        const uint8_t cmd_exit[] = {0xFD, 0xFC, 0xFB, 0xFA, 0x02, 0x00, 0xFE, 0x00, 0x04, 0x03, 0x02, 0x01};
        radarSerial.write(cmd_exit, sizeof(cmd_exit));
        radarSerial.flush();
        delay(50);
        Serial.println("[RADAR] Enabled Engineering Mode on HLK-LD2410");
    }

    // Đọc và phân tích byte stream non-blocking từ UART1 với đồng bộ khung đầu F4 F3 F2 F1
    void loop() {
        if (!is_initialized) return;

        while (radarSerial.available() > 0) {
            uint8_t b = radarSerial.read();

            // 1. Đồng bộ khung đầu: Chỉ nhận khi đúng header F4 F3 F2 F1
            if (rx_idx == 0) {
                if (b == RADAR_HEADER_0) rx_buffer[rx_idx++] = b;
                continue;
            } else if (rx_idx == 1) {
                if (b == RADAR_HEADER_1) rx_buffer[rx_idx++] = b;
                else rx_idx = (b == RADAR_HEADER_0) ? 1 : 0;
                continue;
            } else if (rx_idx == 2) {
                if (b == RADAR_HEADER_2) rx_buffer[rx_idx++] = b;
                else rx_idx = 0;
                continue;
            } else if (rx_idx == 3) {
                if (b == RADAR_HEADER_3) rx_buffer[rx_idx++] = b;
                else rx_idx = 0;
                continue;
            }

            // 2. Nhận phần thân gói tin
            rx_buffer[rx_idx++] = b;

            // 3. Kiểm tra khung đuôi kết thúc: F8 F7 F6 F5
            if (rx_idx >= 8 &&
                rx_buffer[rx_idx - 4] == RADAR_TAIL_0 &&
                rx_buffer[rx_idx - 3] == RADAR_TAIL_1 &&
                rx_buffer[rx_idx - 2] == RADAR_TAIL_2 &&
                rx_buffer[rx_idx - 1] == RADAR_TAIL_3) {

                parse_current_frame();
                rx_idx = 0; // Đặt lại bộ đệm
            }

            // Chống tràn bộ đệm tĩnh
            if (rx_idx >= sizeof(rx_buffer)) {
                rx_idx = 0;
            }
        }
    }

    const RadarStatus_t& get_status() const { return status; }
    bool has_presence() const { return status.has_presence; }
    bool is_approaching() const { return status.is_approaching; }

    // Trả về cự ly gần nhất của mục tiêu thực tế (ưu tiên mục tiêu đang cử động / tiếp cận)
    uint16_t get_distance_cm() const {
        uint16_t d = 0;
        if (status.moving_distance_cm > 0 && status.static_distance_cm > 0) {
            d = min(status.moving_distance_cm, status.static_distance_cm);
        } else if (status.moving_distance_cm > 0) {
            d = status.moving_distance_cm;
        } else if (status.static_distance_cm > 0) {
            d = status.static_distance_cm;
        } else {
            d = status.detect_distance_cm;
        }
        return d;
    }

    uint16_t get_moving_distance_cm() const { return status.moving_distance_cm; }
    uint16_t get_static_distance_cm() const { return status.static_distance_cm; }
    uint8_t get_target_state() const { return status.target_state; }
    uint8_t get_light_level() const { return status.light_level; }

    // Kiểm tra cử chỉ gạt tay cự ly gần (<30cm) để Mute/Cúp máy
    bool check_and_clear_wave_gesture() {
        if (wave_gesture_detected) {
            wave_gesture_detected = false;
            return true;
        }
        return false;
    }

private:
    void parse_current_frame() {
        // Kiểm tra khung đầu: F4 F3 F2 F1
        if (rx_buffer[0] != RADAR_HEADER_0 || rx_buffer[1] != RADAR_HEADER_1 ||
            rx_buffer[2] != RADAR_HEADER_2 || rx_buffer[3] != RADAR_HEADER_3) {
            return;
        }

        // Byte 6: Data Type (0x02 = Normal Target Data, 0x01 = Engineering Data)
        if (rx_buffer[6] == 0x02 || rx_buffer[6] == 0x01) {
            uint8_t state = rx_buffer[8];
            status.target_state = state;
            status.has_presence = (state > 0);

            status.moving_distance_cm = rx_buffer[9] | (rx_buffer[10] << 8);
            status.moving_energy      = rx_buffer[11];

            status.static_distance_cm = rx_buffer[12] | (rx_buffer[13] << 8);
            status.static_energy      = rx_buffer[14];

            status.detect_distance_cm = rx_buffer[15] | (rx_buffer[16] << 8);

            // Cảm biến ánh sáng môi trường (Photosensitive 0 - 255 trên HLK-LD2410)
            if (rx_buffer[6] == 0x01) {
                // Khung Engineering Mode (45 bytes): Cảm biến quang trở nằm ở byte index 37
                if (rx_idx >= 42) {
                    status.light_level = rx_buffer[37];
                }
            } else if (rx_buffer[6] == 0x02) {
                // Radar đang ở Normal Mode (chưa có byte quang trở): kích hoạt Engineering Mode
                static unsigned long last_eng_retry = 0;
                if (millis() - last_eng_retry > 5000) {
                    last_eng_retry = millis();
                    enable_engineering_mode();
                }
            }

            uint16_t cur_dist = get_distance_cm();
            unsigned long now = millis();

            // 1. Thuật toán Vector Tiếp Cận (Approach Vector): d_t < d_{t-1} - 15cm
            if (status.has_presence && cur_dist > 0) {
                if (last_approach_distance > 0 && cur_dist + 15 < last_approach_distance) {
                    status.is_approaching = true;
                } else if (cur_dist > last_approach_distance + 15) {
                    status.is_approaching = false;
                }
                last_approach_distance = cur_dist;
            } else {
                status.is_approaching = false;
                last_approach_distance = 0;
            }

            // 2. Nhận diện Cử Chỉ Gạt Tay Cự Ly Gần (Hand-Wave Gesture: < 30cm, energy > 60 trong 120-400ms)
            uint16_t wave_dist = (status.moving_distance_cm > 0) ? status.moving_distance_cm : cur_dist;
            if (status.has_presence && wave_dist <= 30 && status.moving_energy >= 60) {
                if (wave_gesture_start_ms == 0) {
                    wave_gesture_start_ms = now;
                } else if (now - wave_gesture_start_ms >= 120 && now - wave_gesture_start_ms <= 400) {
                    wave_gesture_detected = true;
                    wave_gesture_start_ms = 0; // Trigger once per wave
                }
            } else {
                if (now - wave_gesture_start_ms > 450) {
                    wave_gesture_start_ms = 0;
                }
            }

            // 3. Điều tiết gửi tin Delta về NAS Hub (Delta distance >= 20cm, đổi trạng thái, đổi độ sáng hoặc 10s heartbeat)
            int16_t dist_diff  = (int16_t)cur_dist - (int16_t)last_sync_distance;
            int16_t light_diff = (int16_t)status.light_level - (int16_t)last_sync_light;
            bool state_changed = (status.has_presence != last_sync_presence);
            bool dist_changed  = (abs(dist_diff) >= 20);
            bool light_changed = (abs(light_diff) >= 5);
            bool heartbeat_due = (now - last_ws_sync_ms >= 10000);

            if (state_changed || (status.has_presence && dist_changed) || light_changed || heartbeat_due) {
                last_ws_sync_ms = now;
                last_sync_presence = status.has_presence;
                last_sync_distance = cur_dist;
                last_sync_light    = status.light_level;

                char json_payload[160];
                snprintf(json_payload, sizeof(json_payload),
                         "{\"type\":\"radar_event\",\"payload\":{\"presence\":%s,\"state\":%u,\"dist_cm\":%u,\"mv_eng\":%u,\"st_eng\":%u,\"approach\":%s,\"light\":%u}}",
                         status.has_presence ? "true" : "false",
                         status.target_state,
                         cur_dist,
                         status.moving_energy,
                         status.static_energy,
                         status.is_approaching ? "true" : "false",
                         status.light_level);

                wsManager.send_text(json_payload);
            }
        }
    }
};

extern RadarLD2410Engine radarEngine;
