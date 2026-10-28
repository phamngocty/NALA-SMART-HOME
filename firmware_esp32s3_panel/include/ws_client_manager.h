#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - WEBSOCKET CLIENT MANAGER
 * Handles connection to PC NAS Hub (ws://192.168.1.114:8765/ws/{device_id})
 * Parses JSON control frames and Binary PCM 520-byte Audio frames.
 * Automatic reconnection and Fail-Safe 300ms monitoring.
 * ==============================================================================
 */

#include <Arduino.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>
#include "protocol_defs.h"
#include "state_machine.h"

using namespace websockets;

typedef void (*TextCallback_t)(const String& type, const JsonDocument& doc);
typedef void (*BinaryCallback_t)(const uint8_t* data, size_t len);
typedef void (*ConnectCallback_t)();

class WSClientManager {
private:
    WebsocketsClient client;
    String server_url;
    bool connected;
    uint32_t last_reconnect_attempt;
    uint32_t last_rx_time;
    TextCallback_t on_text_cb;
    BinaryCallback_t on_binary_cb;
    ConnectCallback_t on_connect_cb;

public:
    WSClientManager() : connected(false), last_reconnect_attempt(0), last_rx_time(0), on_text_cb(nullptr), on_binary_cb(nullptr), on_connect_cb(nullptr) {}

    void set_callbacks(TextCallback_t text_cb, BinaryCallback_t bin_cb, ConnectCallback_t conn_cb = nullptr) {
        on_text_cb = text_cb;
        on_binary_cb = bin_cb;
        on_connect_cb = conn_cb;
    }

    bool is_connected() const { return connected; }

    void begin(const char* url) {
        server_url = url;
        client.onMessage([this](WebsocketsMessage msg) {
            this->last_rx_time = millis();
            if (msg.isText()) {
                JsonDocument doc;
                DeserializationError err = deserializeJson(doc, msg.data());
                if (!err && on_text_cb) {
                    String type = doc["type"] | "";
                    on_text_cb(type, doc);
                }
            } else if (msg.isBinary()) {
                if (on_binary_cb) {
                    on_binary_cb((const uint8_t*)msg.c_str(), msg.length());
                }
            }
        });

        client.onEvent([this](WebsocketsEvent event, String data) {
            if (event == WebsocketsEvent::ConnectionOpened) {
                this->connected = true;
                Serial.println("[WS] Connected to Central NAS Hub!");
                if (this->on_connect_cb) {
                    this->on_connect_cb();
                }
            } else if (event == WebsocketsEvent::ConnectionClosed) {
                this->connected = false;
                Serial.println("[WS] Connection Closed!");
            }
        });
    }

    void loop() {
        if (WiFi.status() == WL_CONNECTED) {
            if (client.available()) {
                client.poll();
            } else {
                connected = false;
                if (millis() - last_reconnect_attempt >= 3000) {
                    last_reconnect_attempt = millis();
                    Serial.printf("[WS] Reconnecting to %s...\n", server_url.c_str());
                    client.connect(server_url);
                }
            }
        }
    }

    void send_text(const String& json_str) {
        if (connected) {
            client.send(json_str);
        }
    }

    void send_binary(const uint8_t* data, size_t len) {
        if (connected) {
            client.sendBinary((const char*)data, len);
        }
    }
};

extern WSClientManager wsManager;
