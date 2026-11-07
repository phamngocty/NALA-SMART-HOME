import os

path = r"firmware_esp32s3_panel\src\main.cpp"
with open(path, "rb") as f:
    content = f.read().decode('utf-8')

old_str = """                // Ngưỡng phát hiện tiếng nói nhạy: rms >= 160 (~30dBFS)
                if (rms >= 160) {
                    last_voice_activity = now;
                    if (!is_wake_streaming) {
                        is_wake_streaming = true;
                        wake_seq = 0;

                        // Xả sạch 560ms âm thanh đệm quá khứ (Pre-Roll) lên Server để nhận diện trọn vẹn từ đầu!
                        if (wake_preroll_buf && wake_ring_count > 0) {
                            uint8_t read_idx = (wake_ring_head + WAKE_PREROLL_FRAMES - wake_ring_count) % WAKE_PREROLL_FRAMES;
                            for (uint8_t f = 0; f < wake_ring_count; f++) {
                                AudioPacket_t wpkt;
                                wpkt.magic = BINARY_MAGIC_WORD; // 0xA55A
                                wpkt.sender_id = my_intercom_id;
                                wpkt.target_id = 0x05; // Target 0x05: Wake Word Scanner
                                wpkt.seq_num = wake_seq++;
                                wpkt.stream_flag = (wake_seq == 1) ? STREAM_FLAG_START : STREAM_FLAG_DATA;
                                memcpy(wpkt.pcm_data, wake_preroll_buf[read_idx], sizeof(wpkt.pcm_data));
                                wpkt.crc8 = calculate_crc8((const uint8_t*)&wpkt, 519);
                                wsManager.send_binary((const uint8_t*)&wpkt, sizeof(AudioPacket_t));
                                read_idx = (read_idx + 1) % WAKE_PREROLL_FRAMES;
                            }
                        }
                    }
                }"""

new_str = """                // Ngưỡng phát hiện tiếng nói siêu nhạy: rms >= 75 (~22dBFS)
                if (rms >= 75) {
                    last_voice_activity = now;
                    if (!is_wake_streaming) {
                        is_wake_streaming = true;
                        wake_seq = 0;
                        Serial.printf("[WAKE-VAD] Voice detected! RMS: %d (nguong: 75) -> Xa 560ms Pre-Roll\\n", (int)rms);

                        // Xả sạch 560ms âm thanh đệm quá khứ (Pre-Roll) lên Server để nhận diện trọn vẹn từ đầu!
                        if (wake_preroll_buf && wake_ring_count > 0) {
                            uint8_t read_idx = (wake_ring_head + WAKE_PREROLL_FRAMES - wake_ring_count) % WAKE_PREROLL_FRAMES;
                            for (uint8_t f = 0; f < wake_ring_count; f++) {
                                AudioPacket_t wpkt;
                                wpkt.magic = BINARY_MAGIC_WORD; // 0xA55A
                                wpkt.sender_id = my_intercom_id;
                                wpkt.target_id = 0x05; // Target 0x05: Wake Word Scanner
                                wpkt.seq_num = wake_seq++;
                                wpkt.stream_flag = (wake_seq == 1) ? STREAM_FLAG_START : STREAM_FLAG_DATA;
                                memcpy(wpkt.pcm_data, wake_preroll_buf[read_idx], sizeof(wpkt.pcm_data));
                                wpkt.crc8 = calculate_crc8((const uint8_t*)&wpkt, 519);
                                wsManager.send_binary((const uint8_t*)&wpkt, sizeof(AudioPacket_t));
                                read_idx = (read_idx + 1) % WAKE_PREROLL_FRAMES;
                                vTaskDelay(pdMS_TO_TICKS(1)); // Chống nghẽn LwIP buffer
                            }
                        }
                    }
                }"""

# Normalize line endings
content_norm = content.replace('\r\n', '\n')
old_str_norm = old_str.replace('\r\n', '\n')
new_str_norm = new_str.replace('\r\n', '\n')

if old_str_norm in content_norm:
    content_norm = content_norm.replace(old_str_norm, new_str_norm)
    with open(path, "wb") as f:
        f.write(content_norm.replace('\n', '\r\n').encode('utf-8'))
    print("SUCCESS")
else:
    print("NOT FOUND")
