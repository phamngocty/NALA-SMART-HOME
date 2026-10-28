#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - WIFI CAPTIVE PORTAL (192.168.4.1)
 * Tự động phát SoftAP "NALA-PANEL-[MÃ]" khi chưa có cấu hình WiFi
 * Cung cấp trang Web cấu hình trực quan, tự quét mạng WiFi xung quanh
 * ==============================================================================
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include "nvs_config_store.h"

class WiFiCaptivePortal {
private:
    DNSServer dnsServer;
    WebServer server;
    NVSConfigStore* pNvs;
    String ap_ssid;
    String mac_suffix;
    bool config_saved;
    uint32_t save_time;

public:
    WiFiCaptivePortal() : server(80), pNvs(nullptr), config_saved(false), save_time(0) {}

    void begin(NVSConfigStore* nvs, const String& suffix) {
        pNvs = nvs;
        mac_suffix = suffix;
        ap_ssid = "NALA-PANEL-" + mac_suffix;

        WiFi.mode(WIFI_AP_STA);
        IPAddress apIP(192, 168, 4, 1);
        IPAddress netMsk(255, 255, 255, 0);
        WiFi.softAPConfig(apIP, apIP, netMsk);
        WiFi.softAP(ap_ssid.c_str());

        Serial.printf("[AP] Phat SoftAP: %s - IP: 192.168.4.1\n", ap_ssid.c_str());

        // DNS Server bắt toàn bộ domain trỏ về 192.168.4.1 (Captive Portal)
        dnsServer.setErrorReplyCode(DNSReplyCode::NoError);
        dnsServer.start(53, "*", apIP);

        // Web Server Routes
        server.on("/", HTTP_GET, [this]() { handle_root(); });
        server.on("/save", HTTP_POST, [this]() { handle_save(); });

        // Captive Portal Detection Endpoints (iOS, Android, Windows)
        server.on("/generate_204", HTTP_GET, [this]() { handle_root(); });
        server.on("/gen_204", HTTP_GET, [this]() { handle_root(); });
        server.on("/hotspot-detect.html", HTTP_GET, [this]() { handle_root(); });
        server.on("/ncsi.txt", HTTP_GET, [this]() { server.send(200, "text/plain", "Microsoft NCSI"); });
        server.on("/connecttest.txt", HTTP_GET, [this]() { handle_root(); });
        server.onNotFound([this]() {
            server.sendHeader("Location", "http://192.168.4.1/", true);
            server.send(302, "text/plain", "");
        });

        server.begin();
        Serial.println("[AP] WebServer 192.168.4.1 san sang!");
    }

    void loop() {
        dnsServer.processNextRequest();
        server.handleClient();

        if (config_saved && millis() - save_time > 2000) {
            Serial.println("[AP] Da luu cau hinh, khoi dong lai ESP32 de ket noi WiFi nha...");
            ESP.restart();
        }
    }

    String get_ap_ssid() const { return ap_ssid; }

private:
    void handle_root() {
        Serial.println("[WEB] Co thiet bi truy cap trang cau hinh WiFi 192.168.4.1");

        // Quét mạng WiFi xung quanh
        int n = WiFi.scanNetworks();
        String wifi_options = "";
        for (int i = 0; i < n; ++i) {
            String ssid = WiFi.SSID(i);
            int32_t rssi = WiFi.RSSI(i);
            if (ssid.length() > 0) {
                wifi_options += "<option value='" + ssid + "'>" + ssid + " (" + String(rssi) + " dBm)</option>\n";
            }
        }
        WiFi.scanDelete();

        String html = R"rawliteral(
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NALA Smart Home - Cài Đặt WiFi</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { background: #0b0f19; color: #f3f4f6; display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 16px; }
        .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 24px; max-width: 400px; width: 100%; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        .header { text-align: center; margin-bottom: 24px; }
        .title { font-size: 20px; font-weight: 800; color: #06b6d4; letter-spacing: 0.5px; }
        .subtitle { font-size: 13px; color: #9ca3af; margin-top: 6px; }
        .badge { display: inline-block; background: #1e3a5f; color: #38bdf8; padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; margin-top: 8px; }
        .form-group { margin-bottom: 16px; }
        label { display: block; font-size: 12px; font-weight: 600; color: #d1d5db; margin-bottom: 6px; text-transform: uppercase; }
        select, input { width: 100%; padding: 12px; background: #1f2937; border: 1px solid #374151; border-radius: 8px; color: #fff; font-size: 14px; outline: none; transition: border 0.2s; }
        select:focus, input:focus { border-color: #06b6d4; }
        .btn { width: 100%; padding: 14px; background: linear-gradient(135deg, #0284c7, #06b6d4); border: none; border-radius: 8px; color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 8px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3); }
        .btn:active { transform: scale(0.98); }
        .footer { font-size: 11px; text-align: center; color: #6b7280; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div class="title">NALA SMART HOME</div>
            <div class="subtitle">Cấu hình kết nối Màn hình Gắn tường</div>
            <div class="badge">THIẾT BỊ: )rawliteral" + ap_ssid + R"rawliteral(</div>
        </div>
        <form action="/save" method="POST">
            <div class="form-group">
                <label>1. Chọn mạng WiFi nhà</label>
                <select name="ssid" id="ssidSelect" onchange="checkCustomSSID(this)">
                    <option value="">-- Chọn mạng WiFi --</option>
                    )rawliteral" + wifi_options + R"rawliteral(
                    <option value="__custom__">+ Nhập tên mạng khác...</option>
                </select>
                <input type="text" name="custom_ssid" id="customSsid" placeholder="Tên WiFi thủ công" style="display:none; margin-top: 8px;">
            </div>
            <div class="form-group">
                <label>2. Mật khẩu WiFi</label>
                <input type="password" name="password" placeholder="Nhập mật khẩu WiFi..." required>
            </div>
            <div class="form-group">
                <label>3. Địa chỉ máy chủ NAS Hub</label>
                <input type="text" name="nas_url" value=")rawliteral" + String(pNvs->get().nas_ws_url) + R"rawliteral(">
            </div>
            <button type="submit" class="btn">LƯU & KẾT NỐI</button>
        </form>
        <div class="footer">Sau khi lưu, màn hình sẽ tự động kết nối vào WiFi nhà bạn.</div>
    </div>
    <script>
        function checkCustomSSID(sel) {
            const customInput = document.getElementById('customSsid');
            if (sel.value === '__custom__') {
                customInput.style.display = 'block';
                customInput.required = true;
            } else {
                customInput.style.display = 'none';
                customInput.required = false;
            }
        }
    </script>
</body>
</html>
)rawliteral";
        server.send(200, "text/html", html);
    }

    void handle_save() {
        String ssid = server.arg("ssid");
        String custom_ssid = server.arg("custom_ssid");
        String pass = server.arg("password");
        String nas_url = server.arg("nas_url");

        if (ssid == "__custom__" && custom_ssid.length() > 0) {
            ssid = custom_ssid;
        }

        if (ssid.length() > 0) {
            strncpy(pNvs->get().wifi_ssid, ssid.c_str(), sizeof(pNvs->get().wifi_ssid));
            strncpy(pNvs->get().wifi_pass, pass.c_str(), sizeof(pNvs->get().wifi_pass));
            if (nas_url.length() > 0) {
                strncpy(pNvs->get().nas_ws_url, nas_url.c_str(), sizeof(pNvs->get().nas_ws_url));
            }
            pNvs->save_immediate();

            String success_html = R"rawliteral(
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đã Lưu Cấu Hình</title>
    <style>
        body { background: #0b0f19; color: #f3f4f6; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: sans-serif; text-align: center; padding: 20px; }
        .box { background: #111827; border: 1px solid #10b981; border-radius: 16px; padding: 32px 24px; max-width: 360px; }
        h2 { color: #10b981; margin-bottom: 12px; }
        p { color: #9ca3af; font-size: 14px; line-height: 1.5; }
    </style>
</head>
<body>
    <div class="box">
        <h2>✓ ĐÃ LƯU THÀNH CÔNG!</h2>
        <p>Màn hình đang khởi động lại để kết nối vào mạng WiFi <strong>)rawliteral" + ssid + R"rawliteral(</strong>.<br><br>Vui lòng quan sát màn hình LCD để nhận mã ghép nối với Web Server!</p>
    </div>
</body>
</html>
)rawliteral";
            server.send(200, "text/html", success_html);
            config_saved = true;
            save_time = millis();
        } else {
            server.send(400, "text/plain", "Loi: Chua chon WiFi");
        }
    }
};
