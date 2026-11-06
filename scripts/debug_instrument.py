# scripts/debug_instrument.py
import re

path_ws = 'firmware_esp32s3_panel/include/ws_client_manager.h'
with open(path_ws, 'r', encoding='utf-8') as f:
    c_ws = f.read()

target_ws = '''        client.onMessage([this](WebsocketsMessage msg) {
            this->last_rx_time = millis();
            if (msg.isText()) {
                JsonDocument doc;
                DeserializationError err = deserializeJson(doc, msg.data());'''

replace_ws = '''        client.onMessage([this](WebsocketsMessage msg) {
            this->last_rx_time = millis();
            if (msg.isText()) {
                Serial.printf("[WS-RX] Text len: %u, FreeHeap: %lu, MaxBlock: %lu\\n",
                              (unsigned int)msg.length(), (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMaxAllocHeap());
                JsonDocument doc;
                DeserializationError err = deserializeJson(doc, msg.data());'''

assert target_ws in c_ws, "target_ws not found"
c_ws = c_ws.replace(target_ws, replace_ws, 1)

with open(path_ws, 'w', encoding='utf-8') as f:
    f.write(c_ws)

# Also instrument main.cpp inside on_ws_text
path_cpp = 'firmware_esp32s3_panel/src/main.cpp'
with open(path_cpp, 'r', encoding='utf-8') as f:
    c_cpp = f.read()

target_cpp = '''    if (type == "ai_state") {'''
replace_cpp = '''    Serial.printf("[WS-TEXT] Handling type: %s, FreeHeap: %lu\\n", type.c_str(), (unsigned long)ESP.getFreeHeap());
    if (type == "ai_state") {'''

assert target_cpp in c_cpp, "target_cpp not found"
c_cpp = c_cpp.replace(target_cpp, replace_cpp, 1)

# Instrument after sync_buttons and sync_all_rooms
target_sync = '''        JsonArrayConst buttons = doc["payload"]["buttons"];
        if (buttons.size() > 0 && taken) {
            uiDashboard.sync_buttons(buttons);
        }
        if (doc["payload"].containsKey("all_rooms") && taken) {
            uiDashboard.sync_all_rooms(doc["payload"]["all_rooms"]);
        }
        if (doc["payload"].containsKey("house_status") && taken) {
            uiDashboard.sync_house_status(doc["payload"]["house_status"]);
        }'''

replace_sync = '''        JsonArrayConst buttons = doc["payload"]["buttons"];
        if (buttons.size() > 0 && taken) {
            Serial.printf("[MAIN] Before sync_buttons: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_buttons(buttons);
            Serial.printf("[MAIN] After sync_buttons: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
        }
        if (doc["payload"].containsKey("all_rooms") && taken) {
            Serial.printf("[MAIN] Before sync_all_rooms: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_all_rooms(doc["payload"]["all_rooms"]);
            Serial.printf("[MAIN] After sync_all_rooms: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
        }
        if (doc["payload"].containsKey("house_status") && taken) {
            Serial.printf("[MAIN] Before sync_house_status: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
            uiDashboard.sync_house_status(doc["payload"]["house_status"]);
            Serial.printf("[MAIN] After sync_house_status: FreeHeap=%lu\\n", (unsigned long)ESP.getFreeHeap());
        }'''

assert target_sync in c_cpp, "target_sync not found"
c_cpp = c_cpp.replace(target_sync, replace_sync, 1)

with open(path_cpp, 'w', encoding='utf-8') as f:
    f.write(c_cpp)

print("Instrumented ws_client_manager.h and main.cpp successfully!")
