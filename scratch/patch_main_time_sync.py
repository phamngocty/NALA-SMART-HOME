import os

main_path = os.path.abspath('firmware_esp32s3_panel/src/main.cpp')
with open(main_path, 'r', encoding='utf-8') as f:
    text = f.read()

is_crlf = '\r\n' in text
nl = '\r\n' if is_crlf else '\n'

# 1. Update on_ws_connected
t1 = f'void on_ws_connected() {{{nl}    send_device_registration();{nl}    if (lvgl_mutex != NULL'
r1 = f'void on_ws_connected() {{{nl}    send_device_registration();{nl}    wsManager.send_text("{{\\"type\\":\\"get_time\\"}}");{nl}    if (lvgl_mutex != NULL'

if t1 in text:
    text = text.replace(t1, r1, 1)
    print("1. Updated on_ws_connected")
else:
    print("1. t1 not found")

# 2. Update RTC sync block
t2 = f'''    // Đồng bộ thời gian thực từ NAS Hub
    if (doc.containsKey("epoch") || doc.containsKey("timestamp")) {{
        unsigned long ep = doc["epoch"] | doc["timestamp"] | 0;
        if (ep > 100000000) {{
            rtc.setTime(ep);
            Serial.printf("[RTC] Dong bo gio tu NAS Hub thanh cong: %s\\n", rtc.getTime("%H:%M:%S").c_str());
        }}
    }}'''

r2 = f'''    // Đồng bộ thời gian thực từ NAS Hub vào RTC nội bộ ESP32Time (chỉ chạy khi server gửi epoch)
    unsigned long ep = 0;
    if (doc.containsKey("epoch")) {{
        ep = doc["epoch"].as<unsigned long>();
    }} else if (doc.containsKey("timestamp")) {{
        ep = doc["timestamp"].as<unsigned long>();
    }} else if (doc["payload"].is<JsonObject>() && doc["payload"].containsKey("epoch")) {{
        ep = doc["payload"]["epoch"].as<unsigned long>();
    }} else if (doc["payload"].is<JsonObject>() && doc["payload"].containsKey("timestamp")) {{
        ep = doc["payload"]["timestamp"].as<unsigned long>();
    }}

    if (ep > 1000000000) {{
        rtc.setTime(ep);
        Serial.printf("[RTC] Dong bo gio thanh cong tu NAS Hub: %s - %s\\n", 
                      rtc.getTime("%H:%M:%S").c_str(), rtc.getTime("%d/%m/%Y").c_str());
        if (taken && uiDashboard.is_screensaver_active()) {{
            String time_str = rtc.getTime("%H:%M");
            String sec_str = rtc.getTime(":%S");
            int wday = rtc.getDayofWeek();
            const char* wday_names[7] = {{"CHỦ NHẬT", "THỨ HAI", "THỨ BA", "THỨ TƯ", "THỨ NĂM", "THỨ SÁU", "THỨ BẢY"}};
            const char* wday_name = (wday >= 0 && wday < 7) ? wday_names[wday] : "HÔM NAY";
            String date_str = rtc.getTime("%d/%m/%Y");
            uiDashboard.update_standby_clock(time_str.c_str(), sec_str.c_str(), wday_name, date_str.c_str());
        }}
    }}

    if (type == "time_sync") {{
        if (taken) xSemaphoreGive(lvgl_mutex);
        return;
    }}'''

t2_crlf = t2.replace('\n', nl)
r2_crlf = r2.replace('\n', nl)

if t2_crlf in text:
    text = text.replace(t2_crlf, r2_crlf, 1)
    print("2. Updated RTC sync block")
elif t2 in text:
    text = text.replace(t2, r2, 1)
    print("2. Updated RTC sync block (LF)")
else:
    print("2. t2 not found")

with open(main_path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Saved firmware_esp32s3_panel/src/main.cpp!")
