import sys

path = 'firmware_esp32s3_panel/src/main.cpp'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Include audio_opus_codec.h và khai báo opusCodec
old_inc = '#include "ui_lvgl_dashboard.h"'
new_inc = '#include "ui_lvgl_dashboard.h"\n#include "audio_opus_codec.h"'

if old_inc in content and '#include "audio_opus_codec.h"' not in content:
    content = content.replace(old_inc, new_inc, 1)
    print("1. Added include audio_opus_codec.h")

old_obj = 'UILVGLDashboard uiDashboard;'
new_obj = 'UILVGLDashboard uiDashboard;\nAudioOpusCodec opusCodec;'

if old_obj in content and 'AudioOpusCodec opusCodec;' not in content:
    content = content.replace(old_obj, new_obj, 1)
    print("2. Added AudioOpusCodec opusCodec instance")

# 2. Khởi tạo trong setup()
old_setup = 'audioEngine.begin();'
new_setup = 'audioEngine.begin();\n    opusCodec.begin(16000, 1, 24000); // Khoi dong Opus Codec 16kHz Mono VoIP'

if old_setup in content and 'opusCodec.begin' not in content:
    content = content.replace(old_setup, new_setup, 1)
    print("3. Added opusCodec.begin() in setup")

# 3. Hỗ trợ giải mã gói Opus trong on_ws_binary
old_bin = 'void on_ws_binary(const uint8_t* data, size_t len) {\n    if (len == BINARY_PACKET_SIZE) {'
new_bin = '''void on_ws_binary(const uint8_t* data, size_t len) {
    if (len >= 9 && *((const uint16_t*)data) == OPUS_MAGIC_WORD) {
        if (is_recording_ptt) return;
        const OpusPacket_t* p = (const OpusPacket_t*)data;
        bool is_ai_or_server = (p->sender_id == 0x00);

        if (p->stream_flag == STREAM_FLAG_START) {
            audioEngine.mute_speaker(false);
            audioEngine.set_speaker_volume(nvsStore.get().speaker_volume);
            rgb_led.setPixelColor(0, rgb_led.Color(56, 189, 248)); // Xanh lo AI Voice
            rgb_led.show();
        } else {
            audioEngine.mute_speaker(false);
        }

        if (p->opus_len > 0) {
            int16_t pcm_decoded[OPUS_FRAME_SAMPLES];
            int decoded = opusCodec.decode_frame(p->payload, p->opus_len, pcm_decoded, OPUS_FRAME_SAMPLES);
            if (decoded > 0) {
                int16_t stereo_out[OPUS_FRAME_SAMPLES * 2];
                for (int s = 0; s < decoded; s++) {
                    int16_t val = pcm_decoded[s];
                    stereo_out[s * 2]     = val;
                    stereo_out[s * 2 + 1] = val;
                }
                size_t written = 0;
                i2s_write(I2S_NUM_0, stereo_out, decoded * 2 * sizeof(int16_t), &written, portMAX_DELAY);
            }
        }

        if (p->stream_flag == STREAM_FLAG_END) {
            delay(120);
            audioEngine.mute_speaker(true);
            rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
            rgb_led.show();
        }
        return;
    }
    if (len == BINARY_PACKET_SIZE) {'''

if old_bin in content and 'OPUS_MAGIC_WORD' not in content:
    content = content.replace(old_bin, new_bin, 1)
    print("4. Added Opus decoding in on_ws_binary")

# 4. Cập nhật handle_mic_streaming để nén bằng Opus khi gửi cho AI
old_stream = '''            pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
            wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
        }
    } else if (was_recording) {
        // Gửi gói tin cờ kết thúc (STREAM_FLAG_END = 0x03) để Server xử lý STT / AI tức thì
        was_recording = false;
        AudioPacket_t pkt;
        memset(&pkt, 0, sizeof(AudioPacket_t));
        pkt.magic = BINARY_MAGIC_WORD;
        pkt.sender_id = my_intercom_id;
        pkt.target_id = ptt_target_id;
        pkt.seq_num = seq++;
        pkt.stream_flag = STREAM_FLAG_END; // 0x03
        pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
        wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
        Serial.println("[AUDIO] Da gui goi ket thuc STREAM_FLAG_END (0x03) len Server NAS!");'''

new_stream = '''            // Neu gui cho AI Server (target == 0x00) va Opus da san sang -> Nen Opus sieu nhe!
            if (ptt_target_id == TARGET_ID_AI_SERVER && opusCodec.is_ready()) {
                static int16_t pcm_acc[OPUS_FRAME_SAMPLES];
                static size_t acc_cnt = 0;

                for (size_t s = 0; s < AUDIO_FRAME_SAMPLES; s++) {
                    pcm_acc[acc_cnt++] = pkt.pcm_data[s];
                    if (acc_cnt >= OPUS_FRAME_SAMPLES) {
                        OpusPacket_t opkt;
                        opkt.magic = OPUS_MAGIC_WORD;
                        opkt.sender_id = my_intercom_id;
                        opkt.target_id = ptt_target_id;
                        opkt.seq_num = seq++;
                        opkt.stream_flag = (seq == 1) ? STREAM_FLAG_START : STREAM_FLAG_DATA;
                        int enc_bytes = opusCodec.encode_frame(pcm_acc, OPUS_FRAME_SAMPLES, opkt.payload, OPUS_MAX_PAYLOAD);
                        if (enc_bytes > 0) {
                            opkt.opus_len = (uint16_t)enc_bytes;
                            wsManager.send_binary((const uint8_t*)&opkt, 9 + enc_bytes);
                        }
                        acc_cnt = 0;
                    }
                }
            } else {
                pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
                wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
            }
        }
    } else if (was_recording) {
        was_recording = false;
        if (ptt_target_id == TARGET_ID_AI_SERVER && opusCodec.is_ready()) {
            OpusPacket_t opkt;
            opkt.magic = OPUS_MAGIC_WORD;
            opkt.sender_id = my_intercom_id;
            opkt.target_id = ptt_target_id;
            opkt.seq_num = seq++;
            opkt.stream_flag = STREAM_FLAG_END;
            opkt.opus_len = 0;
            wsManager.send_binary((const uint8_t*)&opkt, 9);
            Serial.println("[OPUS] Da gui goi ket thuc Opus STREAM_FLAG_END (0x03) len Server NAS!");
        } else {
            AudioPacket_t pkt;
            memset(&pkt, 0, sizeof(AudioPacket_t));
            pkt.magic = BINARY_MAGIC_WORD;
            pkt.sender_id = my_intercom_id;
            pkt.target_id = ptt_target_id;
            pkt.seq_num = seq++;
            pkt.stream_flag = STREAM_FLAG_END; // 0x03
            pkt.crc8 = calculate_crc8((const uint8_t*)&pkt, 519);
            wsManager.send_binary((const uint8_t*)&pkt, sizeof(AudioPacket_t));
            Serial.println("[AUDIO] Da gui goi ket thuc STREAM_FLAG_END (0x03) len Server NAS!");
        }'''

if old_stream in content:
    content = content.replace(old_stream, new_stream, 1)
    print("5. Added Opus encoding in handle_mic_streaming")

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated main.cpp with Opus Codec!")
