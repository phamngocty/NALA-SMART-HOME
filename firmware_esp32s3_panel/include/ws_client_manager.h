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
typedef void (*DisconnectCallback_t)();

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
    DisconnectCallback_t on_disconnect_cb;
    SemaphoreHandle_t ws_mutex;
    QueueHandle_t tx_queue;

public:
    WSClientManager() : connected(false), last_reconnect_attempt(0), last_rx_time(0), 
                        on_text_cb(nullptr), on_binary_cb(nullptr), on_connect_cb(nullptr), on_disconnect_cb(nullptr) {
        ws_mutex = xSemaphoreCreateMutex();
        tx_queue = xQueueCreate(24, sizeof(char*));
    }

    void clear_tx_queue() {
        if (tx_queue == NULL) return;
        char* m = NULL;
        while (xQueueReceive(tx_queue, &m, 0) == pdTRUE) {
            if (m) free(m);
        }
    }

    void set_callbacks(TextCallback_t text_cb, BinaryCallback_t bin_cb, ConnectCallback_t conn_cb = nullptr, DisconnectCallback_t disconn_cb = nullptr) {
        on_text_cb = text_cb;
        on_binary_cb = bin_cb;
        on_connect_cb = conn_cb;
        on_disconnect_cb = disconn_cb;
    }

    bool is_connected() const { return connected; }

    void begin(const char* url) {
        server_url = url;
        client.onMessage([this](WebsocketsMessage msg) {
            this->last_rx_time = millis();
            if (msg.isText()) {
                Serial.printf("[WS-RX] Text len: %u, FreeHeap: %lu, MaxBlock: %lu\n",
                              (unsigned int)msg.length(), (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMaxAllocHeap());
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
                bool was_conn = this->connected;
                this->connected = false;
                Serial.println("[WS] Connection Closed!");
                if (was_conn && this->on_disconnect_cb) {
                    this->on_disconnect_cb();
                }
            }
        });
    }

    void loop() {
        if (WiFi.status() == WL_CONNECTED) {
            if (client.available()) {
                client.poll();
                if (tx_queue != NULL) {
                    char* msg_to_send = NULL;
                    while (xQueueReceive(tx_queue, &msg_to_send, 0) == pdTRUE) {
                        if (msg_to_send) {
                            client.send(msg_to_send);
                            free(msg_to_send);
                        }
                    }
                }
            } else {
                if (connected) {
                    connected = false;
                    clear_tx_queue();
                    if (on_disconnect_cb) on_disconnect_cb();
                }
                if (millis() - last_reconnect_attempt >= 3000) {
                    last_reconnect_attempt = millis();
                    Serial.printf("[WS] Reconnecting to %s...\n", server_url.c_str());
                    client.connect(server_url);
                }
            }
        }
    }

    void send_text(const String& json_str) {
        if (!connected || tx_queue == NULL) return;
        char* copy = strdup(json_str.c_str());
        if (copy) {
            if (xQueueSend(tx_queue, &copy, 0) != pdTRUE) {
                free(copy);
                Serial.println("[WS-TX] Queue full! Dropped message.");
            }
        }
    }

    void send_binary(const uint8_t* data, size_t len) {
        if (connected && ws_mutex && xSemaphoreTake(ws_mutex, pdMS_TO_TICKS(100)) == pdTRUE) {
            client.sendBinary((const char*)data, len);
            xSemaphoreGive(ws_mutex);
        }
    }
};

extern WSClientManager wsManager;
