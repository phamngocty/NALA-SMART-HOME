#pragma once

#include <stdint.h>
#include <stddef.h>

/**
 * ==============================================================================
 * NALA SMART HOME - WEBSOCKET PROTOCOL SPECIFICATIONS
 * Binary Audio Packet (520 Bytes) & CRC-8 Function
 * ==============================================================================
 */

#define BINARY_MAGIC_WORD       0xA55A
#define AUDIO_FRAME_SAMPLES     256     // 256 samples * 2 bytes = 512 bytes PCM 16kHz (~16ms)
#define BINARY_PACKET_SIZE      520

// Stream Flags
#define STREAM_FLAG_START       0x01
#define STREAM_FLAG_DATA        0x02
#define STREAM_FLAG_END         0x03

// Target IDs
#define TARGET_ID_AI_SERVER     0x00
#define TARGET_ID_BROADCAST_ALL 0xFF

// Cấu trúc gói tin nhị phân 520-Byte chuẩn (Packed không đệm)
#pragma pack(push, 1)
typedef struct {
    uint16_t magic;                     // 0..1: 0xA55A (Little-Endian)
    uint8_t  sender_id;                 // 2: ID phòng gửi (0x01, 0x02, ...)
    uint8_t  target_id;                 // 3: ID phòng nhận (0x00: AI Server, 0xFF: All)
    uint16_t seq_num;                   // 4..5: Số thứ tự gói tin tăng dần
    uint8_t  stream_flag;               // 6: 0x01=START, 0x02=DATA, 0x03=END
    int16_t  pcm_data[AUDIO_FRAME_SAMPLES]; // 7..518: 512 bytes âm thanh PCM 16kHz
    uint8_t  crc8;                      // 519: CRC-8 (đa thức 0x07)
} AudioPacket_t;
#pragma pack(pop)

// Kiểm tra kích thước struct tại compile-time
static_assert(sizeof(AudioPacket_t) == 520, "AudioPacket_t must be exactly 520 bytes!");

/**
 * @brief Tính toán Checksum CRC-8 (Đa thức 0x07, Initial 0x00)
 */
inline uint8_t calculate_crc8(const uint8_t *data, size_t length) {
    uint8_t crc = 0x00;
    for (size_t i = 0; i < length; i++) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x80) {
                crc = (crc << 1) ^ 0x07;
            } else {
                crc <<= 1;
            }
        }
    }
    return crc;
}
