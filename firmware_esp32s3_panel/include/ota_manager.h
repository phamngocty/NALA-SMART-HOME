/**
 * NALA SMART HOME - ESP32-S3 OTA FIRMWARE MANAGER
 * Tự động tải stream firmware binary từ NAS Hub qua HTTP Client và nạp Flash với Update.h.
 * Hiển thị giao diện tiến độ tiếng Việt có dấu chuẩn xác qua FontMaker và báo cáo % qua WebSocket.
 */

#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Update.h>
#include "FontMaker.h"
#include "ws_client_manager.h"

// Biến trạng thái toàn cục báo cho LVGL tạm dừng render khi đang nạp OTA
extern volatile bool is_ota_running;

class OTAManager {
public:
    static bool perform_ota(const String& url, size_t expected_size, const String& version, const String& pairing_code, MakeFont* font_maker, LGFX_Device* display, WSClientManager* ws) {
        Serial.printf("[OTA] Bat dau tien trinh OTA Firmware tu: %s (Kich thuoc du kien: %u bytes)\n", url.c_str(), (unsigned int)expected_size);
        
        is_ota_running = true;
        delay(100);

        if (!display) {
            Serial.println("[OTA] Display pointer is NULL!");
            is_ota_running = false;
            return false;
        }

        // 1. Vẽ giao diện thông báo OTA chuyên nghiệp
        display->startWrite();
        display->fillScreen(0x0821); // Nền xanh đen sâu (Dark Navy)
        
        // Header Bar
        display->fillRect(0, 0, 240, 42, 0x18C3);
        display->drawFastHLine(0, 42, 240, 0x07FF);

        if (font_maker) {
            font_maker->set_font(Tahoma16);
            font_maker->print_noBackColor(14, 12, "CẬP NHẬT FIRMWARE OTA", 0x3DF);
        } else {
            display->setTextColor(TFT_CYAN);
            display->drawString("CAP NHAT OTA", 20, 12);
        }

        // Hộp trung tâm thông tin tiến độ
        display->drawRoundRect(10, 56, 220, 220, 8, 0x07FF);
        display->fillRect(11, 57, 218, 218, 0x10A2);

        if (font_maker) {
            font_maker->set_font(Tahoma12);
            font_maker->print_noBackColor(20, 70, "Đang kết nối NAS Hub...", TFT_WHITE);
            font_maker->print_noBackColor(20, 92, "Phiên bản:", TFT_SILVER);
            font_maker->print_noBackColor(95, 92, version.length() > 0 ? version : "v2.5.0", 0x07E0);

            // Thanh tiến độ khung ngoài
            display->drawRoundRect(20, 140, 200, 24, 6, 0x07FF);
            display->fillRect(22, 142, 196, 20, 0x0000);

            font_maker->set_font(Tahoma12);
            font_maker->print_noBackColor(20, 185, "⚠️ VUI LÒNG KHÔNG TẮT NGUỒN", 0xFBE0);
            font_maker->print_noBackColor(20, 210, "Màn hình sẽ tự động khởi động", TFT_SILVER);
            font_maker->print_noBackColor(20, 230, "lại sau khi hoàn tất.", TFT_SILVER);
        }
        display->endWrite();

        // 2. Mở kết nối HTTP Client tải firmware
        HTTPClient http;
        http.begin(url);
        http.setTimeout(25000);
        http.setReuse(false);

        int httpCode = http.GET();
        if (httpCode != HTTP_CODE_OK) {
            Serial.printf("[OTA] HTTP GET thất bại, mã lỗi: %d\n", httpCode);
            display->startWrite();
            if (font_maker) {
                font_maker->set_font(Tahoma12);
                font_maker->print_noBackColor(20, 115, "Lỗi HTTP: " + String(httpCode), TFT_RED);
            }
            display->endWrite();

            if (ws) {
                ws->send_text("{\"type\":\"ota_progress\",\"pairing_code\":\"" + pairing_code + "\",\"progress\":0,\"status\":\"error\",\"message\":\"HTTP Error " + String(httpCode) + "\"}");
            }
            delay(4000);
            is_ota_running = false;
            return false;
        }

        int contentLength = http.getSize();
        if (contentLength <= 0 && expected_size > 0) {
            contentLength = expected_size;
        }

        Serial.printf("[OTA] Content-Length: %d bytes\n", contentLength);

        // 3. Khởi tạo Update Engine vào phân vùng OTA
        if (!Update.begin(contentLength > 0 ? contentLength : UPDATE_SIZE_UNKNOWN, U_FLASH)) {
            Serial.printf("[OTA] Update.begin loi: %s\n", Update.errorString());
            display->startWrite();
            if (font_maker) {
                font_maker->set_font(Tahoma12);
                font_maker->print_noBackColor(20, 115, "Lỗi Flash: " + String(Update.errorString()), TFT_RED);
            }
            display->endWrite();

            if (ws) {
                ws->send_text("{\"type\":\"ota_progress\",\"pairing_code\":\"" + pairing_code + "\",\"progress\":0,\"status\":\"error\",\"message\":\"Flash error: " + String(Update.errorString()) + "\"}");
            }
            delay(4000);
            is_ota_running = false;
            return false;
        }

        // 4. Stream từng khối dữ liệu và ghi vào Flash
        WiFiClient* stream = http.getStreamPtr();
        uint8_t buff[2048];
        size_t written = 0;
        int last_pct = -1;
        unsigned long last_ws_report = 0;

        while (http.connected() && (contentLength <= 0 || written < (size_t)contentLength)) {
            size_t avail = stream->available();
            if (avail) {
                int readBytes = stream->readBytes(buff, ((avail > sizeof(buff)) ? sizeof(buff) : avail));
                if (readBytes > 0) {
                    Update.write(buff, readBytes);
                    written += readBytes;

                    int pct = (contentLength > 0) ? ((written * 100) / contentLength) : 50;
                    if (pct != last_pct) {
                        last_pct = pct;

                        // Vẽ cập nhật thanh tiến độ
                        display->startWrite();
                        int bar_w = (pct * 196) / 100;
                        if (bar_w > 196) bar_w = 196;
                        display->fillRect(22, 142, bar_w, 20, 0x07E0); // Xanh lá
                        display->fillRect(22 + bar_w, 142, 196 - bar_w, 20, 0x0000);

                        // Xóa và vẽ lại chữ %
                        display->fillRect(90, 114, 80, 20, 0x10A2);
                        if (font_maker) {
                            font_maker->set_font(Tahoma12);
                            font_maker->print_noBackColor(95, 116, String(pct) + "%", 0x3DF);
                        }
                        display->endWrite();

                        // Báo cáo qua WebSocket về NAS Hub
                        if (millis() - last_ws_report > 600 || pct >= 100) {
                            last_ws_report = millis();
                            String prog_json = "{\"type\":\"ota_progress\",\"pairing_code\":\"" + pairing_code + 
                                               "\",\"progress\":" + String(pct) + 
                                               ",\"status\":\"downloading\",\"message\":\"Đang ghi Flash: " + String(pct) + "%\"}";
                            if (ws) ws->send_text(prog_json);
                        }
                    }
                }
            } else {
                delay(2);
            }
        }

        http.end();

        // 5. Kết thúc và kiểm tra tính toàn vẹn
        if (Update.end(true)) {
            if (Update.isFinished()) {
                Serial.printf("[OTA] Cập nhật thành công trọn vẹn %u bytes! Khởi động lại...\n", (unsigned int)written);
                
                display->startWrite();
                display->fillRect(22, 142, 196, 20, 0x07E0);
                if (font_maker) {
                    font_maker->set_font(Tahoma12);
                    font_maker->print_noBackColor(20, 255, "✓ CẬP NHẬT THÀNH CÔNG!", 0x07E0);
                }
                display->endWrite();

                if (ws) {
                    ws->send_text("{\"type\":\"ota_progress\",\"pairing_code\":\"" + pairing_code + "\",\"progress\":100,\"status\":\"success\",\"message\":\"Nạp Flash hoàn tất! Đang khởi động lại...\"}");
                }

                delay(1500);
                ESP.restart();
                return true;
            } else {
                Serial.println("[OTA] Update chua hoan tat!");
            }
        } else {
            Serial.printf("[OTA] Update.end failed: %s\n", Update.errorString());
        }

        display->startWrite();
        if (font_maker) {
            font_maker->set_font(Tahoma12);
            font_maker->print_noBackColor(20, 255, "✕ Nạp Flash thất bại!", TFT_RED);
        }
        display->endWrite();

        if (ws) {
            ws->send_text("{\"type\":\"ota_progress\",\"pairing_code\":\"" + pairing_code + "\",\"progress\":0,\"status\":\"error\",\"message\":\"Nạp Flash thất bại: " + String(Update.errorString()) + "\"}");
        }

        delay(4000);
        is_ota_running = false;
        return false;
    }
};
