# 📋 KẾ HOẠCH & ĐẶC TẢ THỰC THI: GIAO DIỆN 4 TAB ĐA PHÒNG & NÂNG CẤP WEBSOCKET

> **Dự án:** NALA SMART HOME - Wall Panel ESP32-S3 (2.8" LCD 240x320) & Central NAS Hub  
> **Phiên bản kiến trúc:** v3.0 (4-Tab Independent Architecture & Multi-Room State Sync)  
> **Ngày phê duyệt:** 01/11/2026

---

## 1. MỤC TIÊU & BÀI TOÁN CẦN GIẢI QUYẾT

### 1.1. Hạn chế của phiên bản cũ (v2.x)
- **Bị giới hạn cứng 4 nút:** Tab 1 dồn ép cả các nút điều khiển thiết bị lẫn hộp thoại AI và nút PTT, chỉ đủ chỗ hiển thị tối đa 4 nút. Khi người dùng cấu hình từ nút thứ 5 trở lên (ví dụ `881C` có 5 nút), nút thứ 5 bị tràn và mất chỗ.
- **Mù thông tin liên phòng:** Màn hình chỉ hiển thị thiết bị của phòng mình, người dùng không thể biết các phòng khác (phòng ngủ, bếp, lầu 3) có đang quên tắt đèn hay không.
- **Hộp thoại AI quá nhỏ:** Câu trả lời văn bản dài từ Gemini/DeepSeek bị cắt cụt, trải nghiệm tương tác giọng nói bị hạn chế.

### 1.2. Giải pháp kiến trúc mới (v3.0 - 4 Tab)
1. **Tách riêng Tab 0 [THIẾT BỊ] và Tab 1 [TRỢ LÝ AI]**: Tối ưu hóa 100% diện tích $240 \times 242\text{ px}$ cho từng tác vụ.
2. **Lưới thiết bị cuộn dọc 2 cột**: Dung tích mở rộng lên 16 nút, cuộn mượt mà qua cơ chế cảm ứng vuốt của LVGL.
3. **Thanh lọc phòng (Room Chips)**: Cho phép chuyển đổi nhanh giữa `[TOÀN NHÀ]` và từng phòng riêng lẻ `[P.Khách]`, `[P.Ngủ Tý]`, `[P.Bếp]`, `[Lầu 3]`.
4. **Thanh cảnh báo toàn nhà & Master Off**: Báo trạng thái trực quan `"X ĐÈN & Y QUẠT ĐANG BẬT"` kèm nút đỏ `[TẮT HẾT]` 1 chạm.
5. **Nâng cấp giao thức WebSocket**: NAS Hub đồng bộ dữ liệu đa phòng (`rooms_summary`) và tiếp nhận lệnh `master_turn_off_all`.

---

## 2. ĐẶC TẢ GIAO DIỆN MÀN HÌNH (LVGL 8.3 ARCHITECTURE)

Kích thước vật lý: **$240 \times 320\text{ px}$** (Portrait)

```
┌─────────────────────────────────────────────────────────────┐
│ 14:35  [WiFi]                        M:[881C] ID:1 (Trần)   │  <-- Header: 0..34px
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [TOÀN NHÀ (7)]  [P.Khách]  [P.Ngủ Tý]  [P.Bếp]  [Lầu 3]     │  <-- Room Chips Bar: 34..62px
│  ─────────────────────────────────────────────────────────  │
│  🟡 3 ĐÈN & 1 QUẠT ĐANG BẬT               [ TẮT HẾT ]        │  <-- Alert & Master Off: 62..86px
│  ─────────────────────────────────────────────────────────  │
│  ┌───────────────────────┐   ┌───────────────────────┐      │
│  │ 💡 Đèn Chùm Trần      │   │ 🌀 Quạt Trần          │      │  <-- Scrollable Device Grid:
│  │ P.KHACH - [ BẬT ]     │   │ P.KHACH - [ BẬT (3) ] │      │      86..276px (Cao 190px)
│  └───────────────────────┘   └───────────────────────┘      │      Cuộn 2 cột mượt mà
│  ┌───────────────────────┐   ┌───────────────────────┐      │
│  │ 💡 Đèn Hắt Trần       │   │ 💡 Đèn Ngủ Bàn        │      │
│  │ P.NGỦ - [ BẬT ]       │   │ P.NGỦ - [ TẮT ]       │      │
│  └───────────────────────┘   └───────────────────────┘      │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│   [🏠 THIẾT BỊ]   [🤖 TRỢ LÝ AI]   [📞 ĐÀM THOẠI]   [⚙️ CÀI ĐẶT]   │  <-- TabBar: 276..320px (Cao 44px)
└─────────────────────────────────────────────────────────────┘
```

### 2.1. Phân bổ kích thước chi tiết
- **Header cố định (Y: 0..34px, H: 34px):** Giờ hệ thống, trạng thái WiFi / WebSocket, Mã Panel, ID phòng.
- **Thanh Bottom TabBar (Y: 276..320px, H: 44px):** 4 Tab đều nhau, mỗi tab rộng đúng $60\text{ px}$:
  - Tab 0: `🏠 THIẾT BỊ`
  - Tab 1: `🤖 TRỢ LÝ AI`
  - Tab 2: `📞 ĐÀM THOẠI`
  - Tab 3: `⚙️ CÀI ĐẶT`
- **Khoang nội dung thân (Body Viewport: Y: 34..276px, H: 242px):**
  - **Tab 0 (Thiết Bị):**
    - Hàng Chip lọc phòng: Cao 28px, cuộn ngang (`LV_SCROLL_DIR_HOR`).
    - Thanh cảnh báo toàn nhà: Cao 24px, nhãn trạng thái màu cam và nút đỏ `[TẮT HẾT]`.
    - Lưới thiết bị cuộn dọc: Cao 190px (`LV_SCROLL_DIR_VER`), chứa tối đa 16 nút ($108 \times 52\text{ px}$ mỗi nút).
  - **Tab 1 (Trợ Lý AI):**
    - Biểu tượng AI Pulse / Waveform động: Cao 60px.
    - Hộp thoại hội thoại cuộn dài (`lv_textarea`): Cao 115px, font tiếng Việt Tahoma 14, tự cuộn xuống cuối khi có tin mới.
    - Nút Push-to-Talk bản to: Kích thước $220 \times 44\text{ px}$ ở đáy khoang nội dung.
  - **Tab 2 (Đàm Thoại):** Lưới 4 phòng chọn kênh và nút giữ nói PTT Intercom 520-byte.
  - **Tab 3 (Cài Đặt):** Thanh trượt âm lượng, độ sáng màn hình, mic gain, chọn model AI, chẩn đoán mạng.

---

## 3. NÂNG CẤP GIAO THỨC WEBSOCKET & SCHEMA DỮ LIỆU

### 3.1. Tin nhắn Cấu Hình Đồng Bộ (`config_sync` từ NAS Hub -> Panel)
Mở rộng payload để gửi toàn bộ danh sách phòng và thiết bị toàn nhà:

```json
{
  "type": "config_sync",
  "payload": {
    "room": "Phòng ngủ ty - tang2",
    "floor": "tang2",
    "my_intercom_id": 1,
    "intercom_targets": [ ... ],
    "my_buttons": [ ... ],
    "all_rooms": [
      {
        "room_name": "Phòng Khách",
        "floor": "Tầng Trệt",
        "buttons": [
          { "id": "btn_1", "name": "Đèn Chùm", "entity_id": "light.den_chum", "icon": "light", "state": "on" },
          { "id": "btn_2", "name": "Quạt Trần", "entity_id": "fan.quat_tran", "icon": "fan", "state": "on" }
        ]
      },
      {
        "room_name": "Phòng Ngủ Tý",
        "floor": "Tầng 2",
        "buttons": [ ... ]
      }
    ],
    "settings": {
      "brightness": 90,
      "volume": 85,
      "ai_model": "gemini"
    }
  }
}
```

### 3.2. Tin nhắn Trạng Thái Toàn Nhà (`house_status_update` từ NAS Hub -> Panel)
Bắn tự động mỗi khi có bất kỳ thực thể nào thay đổi trạng thái trong Home Assistant:

```json
{
  "type": "house_status_update",
  "payload": {
    "total_on_lights": 3,
    "total_on_fans": 1,
    "total_on_devices": 4,
    "entity_changed": {
      "entity_id": "light.den_chum",
      "state": "off"
    }
  }
}
```

### 3.3. Lệnh Tắt Hết Master (`ha_action` từ Panel -> NAS Hub)
Khi người dùng bấm nút đỏ `[TẮT HẾT]`:

```json
{
  "type": "ha_action",
  "source": "panel_881c",
  "payload": {
    "action": "master_turn_off_all",
    "domain": "homeassistant"
  }
}
```
*Phía Server:* `ha_bridge.py` sẽ duyệt danh sách toàn bộ các thực thể đèn (`light.*`) và quạt (`fan.*`) đang có trạng thái `on` và gửi lệnh tắt hàng loạt (batch service call `homeassistant.turn_off`).

---

## 4. LỘ TRÌNH THỰC THI (STEP-BY-STEP IMPLEMENTATION TASKS)

```
[Phase 1] Chuẩn Hóa Cấu Trúc Dữ Liệu & Backend (NAS Hub)
├── T1.1: Bổ sung API & WebSocket Handler cho `all_rooms` và `master_turn_off_all` trong `main_ws_server.py`.
├── T1.2: Bổ sung hàm batch turn-off trong `ha_bridge.py`.
└── T1.3: Cập nhật `devices.json` & deploy lên NAS Hub (`192.168.1.114`).

[Phase 2] Nâng Cấp Firmware Panel ESP32-S3 (LVGL 8.3 & FreeRTOS)
├── T2.1: Tái cấu trúc `ui_lvgl_dashboard.h` từ 3 Tab lên 4 Tab (`buttons[16]`, thanh lọc phòng `room_chips`, `house_alert_strip`, `tab_ai`).
├── T2.2: Nâng cấp xử lý sự kiện cảm ứng (cuộn mượt, lọc phòng theo chip, phản hồi rung/viền sáng).
├── T2.3: Ghép nối callback trong `main.cpp` nhận diện gói tin `config_sync` và `house_status_update` mới.
└── T2.4: Biên dịch Firmware với PlatformIO và chạy chẩn đoán kiểm tra bộ nhớ RAM / Flash.

[Phase 3] Kiểm Thử Thực Tế & Đóng Gói OTA
├── T3.1: Nạp trực tiếp qua cổng COM6 (Panel 2 - D6F4) hoặc nạp qua OTA NAS Hub.
├── T3.2: Kiểm tra chức năng cuộn danh sách 5+ nút, chuyển 4 tab, nút Tắt Hết Master.
└── T3.3: Kiểm tra đàm thoại Intercom và Trợ lý AI trên Tab mới.
```

---

## 5. TIÊU CHÍ NGHIỆM THU (SUCCESS CRITERIA)
1. **Dung tích hiển thị:** Màn hình hiển thị đầy đủ cả 5 nút của `881C` (và mở rộng thoải mái tới 16 nút) qua thanh cuộn dọc mượt mà.
2. **Quan sát liên phòng:** Người dùng ở phòng ngủ nhìn thấy ngay trạng thái đèn phòng khách / phòng bếp đang mở hay tắt.
3. **1 Chạm tắt hết:** Nút `[TẮT HẾT]` tắt thành công toàn bộ đèn/quạt trong nhà chỉ trong $< 300\text{ ms}$.
4. **Trợ lý AI:** Chuyển sang Tab AI hiển thị trọn vẹn văn bản trả lời, không bị cắt cụt.
5. **Hiệu năng & Ổn định:** Tốc độ khung hình LVGL đạt $\ge 30\text{ FPS}$, không giật lag khi cuộn, RAM PSRAM còn trống $\ge 4\text{ MB}$.

