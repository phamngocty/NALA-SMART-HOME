#pragma once

/**
 * ==============================================================================
 * NALA SMART HOME - SYSTEM FINITE STATE MACHINE (FSM)
 * Half-Duplex Acoustic Echo Protection & Safety Transitions
 * ==============================================================================
 */

typedef enum {
    STATE_IDLE = 0,         // Chờ sự kiện (Màn hình bật, mic/loa ở trạng thái nghỉ)
    STATE_AI_LISTENING,     // Đang lắng nghe giọng nói người dùng (Mic ON, Loa MUTE chống vọng)
    STATE_AI_THINKING,      // Đang chờ phản hồi từ Server / Gemini / DeepSeek
    STATE_AI_SPEAKING,      // Đang phát giọng nói AI từ Loa (Loa ON, Mic MUTE)
    STATE_INTERCOM_TX,      // Đang giữ PTT nói sang phòng khác (Mic ON, Loa MUTE)
    STATE_INTERCOM_RX,      // Đang nhận âm thanh từ phòng khác (Loa ON, Mic MUTE)
    STATE_DISCONNECTED,     // Mất kết nối WebSocket / Wi-Fi (Fail-safe 300ms)
    STATE_HARDWARE_TEST     // Chế độ kiểm tra phần cứng độc lập (Phase 1)
} SystemState_t;
