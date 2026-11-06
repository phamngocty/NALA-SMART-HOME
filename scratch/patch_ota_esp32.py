with open('firmware_esp32s3_panel/include/ws_client_manager.h', 'r', encoding='utf-8') as f:
    ws_code = f.read()

target_ws = '''    void send_binary(const uint8_t* data, size_t len) {
        if (connected && ws_mutex && xSemaphoreTake(ws_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            client.sendBinary((const char*)data, len);
            xSemaphoreGive(ws_mutex);
        }
    }'''

repl_ws = '''    void send_text_direct(const String& json_str) {
        if (connected && ws_mutex && xSemaphoreTake(ws_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            client.send(json_str);
            client.poll();
            xSemaphoreGive(ws_mutex);
        }
    }

    void send_binary(const uint8_t* data, size_t len) {
        if (connected && ws_mutex && xSemaphoreTake(ws_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            client.sendBinary((const char*)data, len);
            xSemaphoreGive(ws_mutex);
        }
    }'''

ws_norm = ws_code.replace('\r\n', '\n')
target_ws_norm = target_ws.replace('\r\n', '\n')
repl_ws_norm = repl_ws.replace('\r\n', '\n')

if target_ws_norm in ws_norm:
    new_ws = ws_norm.replace(target_ws_norm, repl_ws_norm)
    with open('firmware_esp32s3_panel/include/ws_client_manager.h', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_ws)
    print("SUCCESS: Updated ws_client_manager.h")
else:
    print("ERROR: Target not found in ws_client_manager.h")

# Update ota_manager.h
with open('firmware_esp32s3_panel/include/ota_manager.h', 'r', encoding='utf-8') as f:
    ota_code = f.read()

new_ota = ota_code.replace('ws->send_text(', 'ws->send_text_direct(')
with open('firmware_esp32s3_panel/include/ota_manager.h', 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(new_ota)
print("SUCCESS: Updated ota_manager.h")
