#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - HARDWARE OPUS CODEC ENGINE FOR ESP32-S3
 * Voice compression & decompression using Xiph.Org libopus (OPUS_APPLICATION_VOIP)
 * - Sample Rate: 16,000 Hz Mono
 * - Frame Size: 20ms (320 samples / 640 bytes raw PCM -> ~45-65 bytes Opus)
 * - Bandwidth Reduction: Từ 32.5 KB/s giảm xuống còn ~3.0 - 3.5 KB/s (~90% tiết kiệm)
 * ==============================================================================
 */

#include <Arduino.h>
#include <opus.h>
#include "protocol_defs.h"

class AudioOpusCodec {
private:
    OpusEncoder* encoder = nullptr;
    OpusDecoder* decoder = nullptr;
    bool is_initialized = false;

public:
    AudioOpusCodec() = default;

    ~AudioOpusCodec() {
        end();
    }

    bool begin(int sample_rate = 16000, int channels = 1, int bitrate = 24000) {
        if (is_initialized) return true;

        int enc_err = OPUS_OK;
        encoder = opus_encoder_create(sample_rate, channels, OPUS_APPLICATION_VOIP, &enc_err);
        if (enc_err != OPUS_OK || !encoder) {
            Serial.printf("[OPUS] Error creating encoder: %d\n", enc_err);
            return false;
        }

        // Tối ưu CPU cho vi điều khiển ESP32-S3
        opus_encoder_ctl(encoder, OPUS_SET_BITRATE(bitrate));
        opus_encoder_ctl(encoder, OPUS_SET_COMPLEXITY(0)); // 0 = tối thiểu CPU, không giật lag FreeRTOS
        opus_encoder_ctl(encoder, OPUS_SET_SIGNAL(OPUS_SIGNAL_VOICE));
        opus_encoder_ctl(encoder, OPUS_SET_VBR(1)); // Variable bitrate

        int dec_err = OPUS_OK;
        decoder = opus_decoder_create(sample_rate, channels, &dec_err);
        if (dec_err != OPUS_OK || !decoder) {
            Serial.printf("[OPUS] Error creating decoder: %d\n", dec_err);
            if (encoder) {
                opus_encoder_destroy(encoder);
                encoder = nullptr;
            }
            return false;
        }

        is_initialized = true;
        Serial.printf("[OPUS] Engine ready! Rate: %dHz, Channels: %d, Bitrate: %d bps\n",
                      sample_rate, channels, bitrate);
        return true;
    }

    void end() {
        if (encoder) {
            opus_encoder_destroy(encoder);
            encoder = nullptr;
        }
        if (decoder) {
            opus_decoder_destroy(decoder);
            decoder = nullptr;
        }
        is_initialized = false;
    }

    bool is_ready() const {
        return is_initialized;
    }

    // Nén raw PCM (320 mẫu int16 = 20ms @ 16kHz) thành Opus payload
    // Trả về số byte nén thực tế (> 0) hoặc mã lỗi (< 0)
    int encode_frame(const int16_t* pcm_samples, int frame_size, uint8_t* opus_out, int max_out_bytes) {
        if (!is_initialized || !encoder) return -1;
        return opus_encode(encoder, pcm_samples, frame_size, opus_out, max_out_bytes);
    }

    // Giải mã Opus payload thành raw PCM
    // Trả về số mẫu giải mã được (> 0) hoặc mã lỗi (< 0)
    int decode_frame(const uint8_t* opus_in, int in_bytes, int16_t* pcm_out, int max_samples) {
        if (!is_initialized || !decoder) return -1;
        return opus_decode(decoder, opus_in, in_bytes, pcm_out, max_samples, 0);
    }
};

extern AudioOpusCodec opusCodec;
