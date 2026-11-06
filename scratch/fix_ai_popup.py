with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''void on_ws_binary(const uint8_t* data, size_t len) {
    if (len == BINARY_PACKET_SIZE) {
        const AudioPacket_t* p = (const AudioPacket_t*)data;
        if (p->magic == BINARY_MAGIC_WORD) {
            // Half-duplex: Nếu đang giữ nút nói thì không phát để chống feedback
            if (is_recording_ptt) return;

            if (p->stream_flag == STREAM_FLAG_START) {
                char caller_buf[64];
                uiDashboard.get_caller_display(p->sender_id, caller_buf, sizeof(caller_buf));
                bool ring = nvsStore.get().ring_on_call;

                bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                if (taken) {
                    uiDashboard.show_incoming_call(caller_buf, ring);
                    uiDashboard.set_intercom_status("Cuộc gọi đến...", 0xF59E0B);
                    xSemaphoreGive(lvgl_mutex);
                }

                rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương
                rgb_led.show();

                audioEngine.mute_speaker(false);
                audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
                if (ring) {
                    audioEngine.play_ringtone(); // Đổ chuông du dương Ding-Dong to rõ
                    taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                    if (taken) {
                        uiDashboard.show_incoming_call(caller_buf, false);
                        xSemaphoreGive(lvgl_mutex);
                    }
                }
                Serial.printf("[INTERCOM] Cuộc gọi đến từ ID 0x%02X (%s) - Đổ chuông: %d\\n", p->sender_id, caller_buf, ring);
            } else {
                audioEngine.mute_speaker(false);
            }

            // Phát âm thanh stereo ra Loa qua I2S DMA
            int16_t stereo_out[AUDIO_FRAME_SAMPLES * 2];
            for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                int16_t val = p->pcm_data[s];
                stereo_out[s * 2]     = val;
                stereo_out[s * 2 + 1] = val;
            }
            size_t written = 0;
            i2s_write(I2S_NUM_0, stereo_out, sizeof(stereo_out), &written, portMAX_DELAY);

            if (p->stream_flag == STREAM_FLAG_END) {
                delay(200); // Đợi 200ms để DMA phát hết trọn vẹn từ cuối câu trước khi ngắt amply
                audioEngine.mute_speaker(true);
                rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Trở lại xanh lá
                rgb_led.show();

                bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                if (taken) {
                    uiDashboard.hide_incoming_call();
                    uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                    xSemaphoreGive(lvgl_mutex);
                }
                Serial.println("[INTERCOM] Kết thúc cuộc gọi.");
            }
        }
    }
}'''

replacement = '''void on_ws_binary(const uint8_t* data, size_t len) {
    if (len == BINARY_PACKET_SIZE) {
        const AudioPacket_t* p = (const AudioPacket_t*)data;
        if (p->magic == BINARY_MAGIC_WORD) {
            // Half-duplex: Nếu đang giữ nút nói thì không phát để chống feedback
            if (is_recording_ptt) return;

            // Phân biệt: sender_id == 0x00 là âm thanh phản hồi từ AI Nala / Server Hub
            // sender_id >= 0x01 là cuộc gọi Intercom đàm thoại nội bộ giữa các phòng
            bool is_ai_or_server = (p->sender_id == 0x00);

            if (p->stream_flag == STREAM_FLAG_START) {
                if (!is_ai_or_server) {
                    char caller_buf[64];
                    uiDashboard.get_caller_display(p->sender_id, caller_buf, sizeof(caller_buf));
                    bool ring = nvsStore.get().ring_on_call;

                    bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                    if (taken) {
                        uiDashboard.show_incoming_call(caller_buf, ring);
                        uiDashboard.set_intercom_status("Cuộc gọi đến...", 0xF59E0B);
                        xSemaphoreGive(lvgl_mutex);
                    }

                    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255)); // Xanh dương (Intercom)
                    rgb_led.show();

                    audioEngine.mute_speaker(false);
                    audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
                    if (ring) {
                        audioEngine.play_ringtone(); // Đổ chuông du dương Ding-Dong to rõ
                        taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                        if (taken) {
                            uiDashboard.show_incoming_call(caller_buf, false);
                            xSemaphoreGive(lvgl_mutex);
                        }
                    }
                    Serial.printf("[INTERCOM] Cuộc gọi đến từ ID 0x%02X (%s) - Đổ chuông: %d\\n", p->sender_id, caller_buf, ring);
                } else {
                    // Âm thanh phản hồi từ AI Nala: KHÔNG hiện popup cuộc gọi nội bộ, KHÔNG đổ chuông intercom
                    rgb_led.setPixelColor(0, rgb_led.Color(56, 189, 248)); // Xanh lơ (Sky blue - AI Voice)
                    rgb_led.show();

                    audioEngine.mute_speaker(false);
                    audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
                    Serial.println("[AI VOICE] Nhận âm thanh phản hồi từ AI Nala (không hiện popup intercom)...");
                }
            } else {
                audioEngine.mute_speaker(false);
            }

            // Phát âm thanh stereo ra Loa qua I2S DMA
            int16_t stereo_out[AUDIO_FRAME_SAMPLES * 2];
            for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                int16_t val = p->pcm_data[s];
                stereo_out[s * 2]     = val;
                stereo_out[s * 2 + 1] = val;
            }
            size_t written = 0;
            i2s_write(I2S_NUM_0, stereo_out, sizeof(stereo_out), &written, portMAX_DELAY);

            if (p->stream_flag == STREAM_FLAG_END) {
                delay(200); // Đợi 200ms để DMA phát hết trọn vẹn từ cuối câu trước khi ngắt amply
                audioEngine.mute_speaker(true);
                rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0)); // Trở lại xanh lá
                rgb_led.show();

                if (!is_ai_or_server) {
                    bool taken = (xSemaphoreTake(lvgl_mutex, pdMS_TO_TICKS(50)) == pdTRUE);
                    if (taken) {
                        uiDashboard.hide_incoming_call();
                        uiDashboard.set_intercom_status("Đàm thoại: Sẵn sàng", 0x10B981);
                        xSemaphoreGive(lvgl_mutex);
                    }
                    Serial.println("[INTERCOM] Kết thúc cuộc gọi.");
                } else {
                    Serial.println("[AI VOICE] Đã phát xong âm thanh AI Nala.");
                }
            }
        }
    }
}'''

content_norm = content.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in content_norm:
    new_content = content_norm.replace(target_norm, replacement_norm)
    with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_content)
    print('SUCCESS: Updated main.cpp')
else:
    print('ERROR: target_norm not found')
