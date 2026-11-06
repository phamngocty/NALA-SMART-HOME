# 🛡️ AGENT DIRECTIVE: REPO TRỰC TIẾP & BÁO CÁO THỰC THẾ DỰ ÁN NALA SMART HOME
## GROUND TRUTH SPECIFICATION & AGENT GUIDELINES (v3.3.1-STABLE)

> **TÀI LIỆU KHÓA NGỮ CẢNH (GROUND TRUTH SPECIFICATION)**  
> *Được chuẩn hóa theo kỹ năng `ground-truth-sync` (Reconnaissance First).*  
> Mọi AI Agent (Antigravity, Cursor, Copilot, Claude, Gemini Web) khi làm việc trong repository này **BẮT BUỘC** phải tuân thủ các thông số kỹ thuật và cấu hình phần cứng đã kiểm chứng bên dưới. Tuyệt đối **KHÔNG** tự ý suy diễn hoặc thay đổi chân GPIO, cấu trúc gói tin hoặc quy trình build.

---

## 1. NGUYÊN TẮC BẮT BUỘC (THE GROUND TRUTH RULES)

1. **Repository & Mạch Vật Lý Là Sự Thật Duy Nhất:** Mã nguồn đang chạy và sơ đồ mạch (`es3c28p_schematic.pdf`) quyết định việc thực thi. Kế hoạch từ các mô hình AI Web chỉ mang tính tham khảo.
2. **Ràng Buộc Bộ Nhớ Cực Hạn (Zero PSRAM):** Bo mạch thực tế là ESP32-S3 DevKitC-1 N8 **KHÔNG CÓ PSRAM NGOÀI** (`PSRAM: 0.00 MB free`). Toàn bộ FreeRTOS, WiFi, WebSocket, LVGL, Audio đều chia sẻ 320 KB SRAM nội bộ.
   - **Free Heap** phải luôn $\ge 110\text{ KB}$.
   - **MaxBlock** phải luôn $\ge 50\text{ KB}$.
   - Cấm cấp phát động widget LVGL khi chuyển phòng hoặc nhận gói tin WebSocket.
   - Gói tin WebSocket JSON gửi từ server tới ESP32 không được vượt quá $3 - 4\text{ KB}$.
3. **Audio Codec Chuyên Dụng:** Mạch sử dụng IC Codec **Everest ES8311** (I2C addr `0x18`) và IC khuếch đại **SC8002B** (kích hoạt bằng mức `LOW` trên chân `PA_EN = GPIO 1`), cấp xung `I2S_MCLK = GPIO 4` ($4.096\text{ MHz}$).
4. **Bảo Toàn Quy Trình Nạp & Build:** Dự án sử dụng PlatformIO (Arduino + ESP-IDF Direct Drivers). Build lệnh:
   ```powershell
   & "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -d firmware_esp32s3_panel
   ```
5. **Deploy Tự Động Qua NAS Hub:** Không tự xóa hoặc sửa đổi API deploy OTA (`deploy_to_nas.py` và `http://192.168.1.114:8765/api/ota/upload`).

---

## 2. THÔNG SỐ PHẦN CỨNG ĐÃ KIỂM CHỨNG (VERIFIED HARDWARE)

### 2.1. Thiết Bị Đầu Cuối (Panel Cảm Ứng Gắn Tường)
- **Model bo mạch:** LCDWiki ES3C28P (2.8" ESP32-S3 Capacitive Touch IPS Display).
- **Vi điều khiển:** ESP32-S3 (Xtensa dual-core LX7 240MHz).
- **Bộ nhớ thực tế:** 16MB Flash (DIO/QIO), **0MB PSRAM** (320 KB SRAM nội bộ).
- **Danh sách thiết bị thực tế đang hoạt động trong mạng:**
  1. **Panel 1 (`881C`):** IP `192.168.1.107`, ID 1 (`Phòng ngủ Tý`) — Phiên bản v3.3.1.
  2. **Panel 2 (`D6F4`):** IP `192.168.1.110`, ID 2 (`Phòng chiếu`) — Phiên bản v3.3.1 — Đang cắm USB trực tiếp vào máy dev qua cổng `COM6`.

### 2.2. Bảng Sơ Đồ Chân (Hardware Pinout Table)

| Ngoại vi | Tên chân mạch | GPIO ESP32-S3 | Chế độ / Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- |
| **I2C Bus (Chung)** | SCL | **GPIO 15** | Kéo trở 4.7kΩ lên 3.3V |
| | SDA | **GPIO 16** | Kéo trở 4.7kΩ lên 3.3V |
| **Audio Codec ES8311** | I2C Addr | **0x18** | Cấu hình 69 thanh ghi Everest Semi |
| | I2S MCLK | **GPIO 4** | $256 \times F_s = 4.096\text{ MHz}$ (Master Clock bắt buộc) |
| | I2S BCLK | **GPIO 5** | Bit Clock ($512\text{ kHz}$) |
| | I2S LRCK | **GPIO 7** | Word Select (WS, $16\text{ kHz}$) |
| | I2S DOUT | **GPIO 8** | Dữ liệu phát ra loa (DAC) |
| | I2S DIN | **GPIO 6** | Dữ liệu thu từ Microphone onboard (ADC) |
| **Amply Loa SC8002B** | PA_EN | **GPIO 1** | **Active LOW**: `LOW` = Bật amply ra loa, `HIGH` = Mute amply |
| **Màn Hình LCD 2.8"** | ST7789/ILI9341V | SPI2_HOST | Độ phân giải 240x320 |
| | LCD MOSI | **GPIO 11** | SPI Data |
| | LCD SCLK | **GPIO 12** | SPI Clock |
| | LCD MISO | **GPIO 13** | SPI MISO |
| | LCD CS | **GPIO 10** | Chip Select |
| | LCD DC | **GPIO 46** | Data / Command |
| | LCD RST | **-1** | Nối trực tiếp chân EN / Hardware Reset |
| | LCD Backlight | **GPIO 45** | PWM kênh 0, 5000Hz (GPIO 21 là chân phụ) |
| **Cảm Ứng Điện Dung** | FT6336U/CST328 | I2C `0x38`/`0x1A` | Cảm ứng đa điểm điện dung |
| | Touch INT | **GPIO 17** | Ngắt chạm tay |
| | Touch RST | **GPIO 18** | Reset IC cảm ứng (Active LOW) |
| **RGB LED SMD** | Data | **GPIO 42** | Đèn WS2812 (NeoPixel) mặt sau bo mạch |
| **Nút Nhấn Vật Lý** | BOOT | **GPIO 0** | Nút nhấn kéo xuống GND khi nhấn |
| **Thẻ Nhớ MicroSD** | SDIO 4-Bit | GPIO 38, 40, 39, 41, 48, 47 | Giao tiếp SD-MMC 4 đường dữ liệu |

---

## 3. PHÂN VÙNG BỘ NHỚ FLASH (16MB PARTITION SCHEME)

Tệp định nghĩa: `firmware_esp32s3_panel/partitions.csv`

```csv
# Name,   Type, SubType, Offset,   Size,     Flags
nvs,      data, nvs,     0x9000,   0x5000,   (20 KB)
otadata,  data, ota,     0xe000,   0x2000,   (8 KB)
app0,     app,  ota_0,   0x10000,  0x300000, (3 MB - Phân vùng OTA 1)
app1,     app,  ota_1,   0x310000, 0x300000, (3 MB - Phân vùng OTA 2)
spiffs,   data, spiffs,  0x610000, 0x1E0000, (1.875 MB)
coredump, data, coredump,0x7F0000, 0x10000,  (64 KB)
```

---

## 4. HẠ TẦNG SERVER VÀ GIAO THỨC TRUYỀN THÔNG

### 4.1. Máy Chủ Trung Tâm (NAS Hub)
- **Địa chỉ:** `192.168.1.114:8765`
- **Tài khoản SSH:** `ssh nas152@192.168.1.114` (Password: `271000`)
- **Admin Dashboard:** `http://192.168.1.114:8765/admin`
- **Container Docker:** `nala_nas_ws_hub` (Mount thư mục `/home/nas152/nala-voice-intercom-system/server_nas_hub/app`)
- **Thành phần phần mềm:**
  - `main_ws_server.py`: FastAPI + WebSockets điều phối kết nối từ Panel và Trình duyệt. Đã tinh gọn payload `ha_state_change` xuống ~300-800 bytes để chống tràn RAM trên ESP32.
  - `ha_bridge.py`: Cầu nối hai chiều tới Home Assistant (`192.168.1.27:8123`).
  - `intercom_router.py`: Chuyển tiếp luồng âm thanh đàm thoại 520 bytes PCM giữa các phòng.
  - `ai_agent_router.py`: Tích hợp Gemini API và DeepSeek API.

### 4.2. Giao Thức Gói Tin Đàm Thoại Intercom (520 Bytes Binary Frame)
```text
Byte 0..1   (uint16_t): Magic Word = 0xA55A (Little-Endian)
Byte 2      (uint8_t) : sender_id  (0x01: Panel 1, 0x02: Panel 2, ...)
Byte 3      (uint8_t) : target_id  (0x00: AI Server, 0x01..0xFE: Room ID, 0xFF: Toàn nhà)
Byte 4..5   (uint16_t): seq_num    (Số thứ tự gói tin tăng dần)
Byte 6      (uint8_t) : stream_flag(0x01: START, 0x02: STREAMING_PCM, 0x03: END)
Byte 7..518 (int16_t[256]): 512 Bytes dữ liệu PCM 16kHz Mono (16ms audio)
Byte 519    (uint8_t) : Checksum CRC-8 (đa thức 0x07)
```

---

## 5. KIẾN TRÚC GIAO DIỆN V3.3.1 (ZERO-RAM SMART FLOOR & ROOM HUB)

- **Cơ chế phân bổ 4 Tab đáy (60px/tab):**
  - Tab 0: `🏠 THIẾT BỊ` — Lưới 2 cột cuộn dọc mượt mà (mảng tĩnh 16 nút bấm).
    - Thanh Chip lọc phòng: Nút `[TOÀN NHÀ]` và các chip phòng.
    - Chế độ Toàn Nhà (`ALL_HOUSE_VIEW`): Các nút phòng đang bật thiết bị hiển thị màu Cam/Đỏ; phòng tắt hiển thị Xanh/Xám dịu.
    - Chế độ Phòng từ xa (`REMOTE_ROOM`): Tái sử dụng 16 nút bấm có sẵn để nạp danh sách thiết bị phòng được chọn; xuất hiện nút `[QUAY VỀ PHÒNG CHÍNH]`.
    - Bộ hẹn giờ tự động quay về (`room_view_timeout_sec`, mặc định 30s): Tự động hồi hương về phòng chính sau thời gian không chạm.
    - Thanh tóm tắt toàn nhà: Dải cảnh báo có nút `[TẮT HẾT]` 1 chạm.
  - Tab 1: `🤖 TRỢ LÝ AI` — Khung chat cuộn hiển thị phản hồi từ Gemini/DeepSeek và nút PTT lớn.
  - Tab 2: `📞 ĐÀM THOẠI` — Kênh Intercom 520-byte gọi từng phòng hoặc gọi toàn nhà.
  - Tab 3: `⚙️ CÀI ĐẶT` — Chỉnh âm lượng, độ sáng, mic gain, model AI, OTA.

---

## 6. MỐC PHÁT HÀNH & QUY TRÌNH ROLLBACK

### 6.1. Danh Sách Bản Dựng Đã Kiểm Chứng (Verified Releases)
- **v3.3.1-stable** (Commit `ff27896` / Tag `v3.3.1-stable` / Branch `release-v3.3.1`):
  - File binary: `nas_firmware_backup/firmware_v3.3.1_stable.bin` (MD5: `82AC754F062799FBE82D6225151DE010`).
  - Hỗ trợ đầy đủ Toàn Nhà Zero-RAM và tối ưu hóa payload WebSocket server NAS.
- **v3.2.1-stable** (Commit `706622f` / Tag `v3.2.1-stable` / Branch `release-v3.2.1`):
  - File binary: `nas_firmware_backup/firmware_v3.2.1_stable.bin`.
  - Bản ổn định kinh điển với Loa, Mic, Cảm ứng hoàn hảo.

### 6.2. Lệnh Nạp Cứu Hộ Rollback (Flash đè bằng esptool):
```powershell
# Rollback về v3.3.1-stable
& "$env:USERPROFILE\.platformio\penv\Scripts\python.exe" "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32s3 --port COM6 --baud 921600 write_flash 0x10000 "nas_firmware_backup\firmware_v3.3.1_stable.bin"

# Hoặc Rollback về v3.2.1-stable
& "$env:USERPROFILE\.platformio\penv\Scripts\python.exe" "$env:USERPROFILE\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32s3 --port COM6 --baud 921600 write_flash 0x10000 "nas_firmware_backup\firmware_v3.2.1_stable.bin"
```
