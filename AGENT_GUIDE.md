# 🛡️ AGENT DIRECTIVE: REPO TRỰC TIẾP & BÁO CÁO THỰC THẾ DỰ ÁN NALA SMART HOME

> **TÀI LIỆU KHÓA NGỮ CẢNH (GROUND TRUTH SPECIFICATION)**  
> *Được tạo tự động theo kỹ năng `ground-truth-sync` (Reconnaissance First).*  
> Mọi AI Agent (Antigravity, Cursor, Copilot, Claude, Gemini) khi làm việc trong repository này **BẮT BUỘC** phải tuân thủ các thông số kỹ thuật và cấu hình phần cứng đã kiểm chứng bên dưới. Tuyệt đối **KHÔNG** tự ý suy diễn hoặc thay đổi chân GPIO, cấu trúc gói tin hoặc quy trình build.

---

## 1. NGUYÊN TẮC BẮT BUỘC (THE GROUND TRUTH RULES)

1. **Repository & Mạch Vật Lý Là Sự Thật Duy Nhất:** Mã nguồn đang chạy và sơ đồ mạch (`es3c28p_schematic.pdf`) quyết định việc thực thi. Kế hoạch từ các mô hình AI Web chỉ mang tính tham khảo.
2. **Không Ảo Giác Ngoại Vi:** Mạch sử dụng IC Codec chuyên dụng **Everest ES8311** và IC khuếch đại **SC8002B**, không phải I2S thô hay DAC nội.
3. **Bảo Toàn Quy Trình Nạp & Build:** Dự án sử dụng PlatformIO (Arduino + ESP-IDF Direct Drivers). Build lệnh:
   ```powershell
   & "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run -d firmware_esp32s3_panel
   ```
4. **Deploy Tự Động Qua NAS Hub:** Không tự xóa hoặc sửa đổi API deploy OTA (`deploy_to_nas.py` và `http://192.168.1.114:8765/api/ota/upload`).

---

## 2. THÔNG SỐ PHẦN CỨNG ĐÃ KIỂM CHỨNG (VERIFIED HARDWARE)

### 2.1. Thiết Bị Đầu Cuối (Panel Cảm Ứng Gắn Tường)
- **Model bo mạch:** LCDWiki ES3C28P (2.8" ESP32-S3 Capacitive Touch IPS Display).
- **Vi điều khiển:** ESP32-S3 (ESP32-S3R8, Xtensa dual-core LX7 240MHz).
- **Bộ nhớ:** 16MB Flash (QIO), 8MB Octal PSRAM (OPI).
- **Danh sách thiết bị thực tế đang hoạt động trong mạng:**
  1. **Panel 1 (`881C`):** IP `192.168.1.121`, ID 1 (`Phòng ngủ Tý`).
  2. **Panel 2 (`D6F4`):** IP `192.168.1.128`, ID 2 (`Phòng chiếu`) — Đang cắm USB trực tiếp vào máy dev qua cổng `COM6`.

### 2.2. Bảng Sơ Đồ Chân (Hardware Pinout Table)

| Ngoại vi | Tên chân mạch | GPIO ESP32-S3 | Chế độ / Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- |
| **I2C Bus (Chung)** | SCL | **GPIO 15** | Kéo trở 4.7kΩ lên 3.3V |
| | SDA | **GPIO 16** | Kéo trở 4.7kΩ lên 3.3V |
| **Audio Codec ES8311** | I2C Addr | **0x18** | Cấu hình 69 thanh ghi Everest Semi |
| | I2S MCLK | **GPIO 4** | $256 \times F_s = 4.096\text{ MHz}$ (Master Clock bắt buộc) |
| | I2S BCLK | **GPIO 5** | Bit Clock |
| | I2S LRCK | **GPIO 7** | Word Select (WS) |
| | I2S DOUT | **GPIO 8** | Dữ liệu phát ra loa (đồng thời route GPIO Matrix sang GPIO 6) |
| | I2S DIN | **GPIO 6** | Dữ liệu thu từ Microphone onboard |
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
- **Thành phần phần mềm:**
  - `main_ws_server.py`: FastAPI + WebSockets điều phối kết nối từ Panel và Trình duyệt.
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

## 5. BÁO CÁO ĐỐI CHIẾU & PHÁT HIỆN LỆCH PHA (GAP ANALYSIS)

| Hạng mục | Bản kế hoạch lý thuyết (Gemini Web) | Thực tế đang hoạt động trong Repository | Đánh giá sai lệch & Biện pháp xử lý |
| :--- | :--- | :--- | :--- |
| **IC Codec Âm Thanh** | Nghĩ rằng phần cứng chỉ dùng DAC nội hoặc IC thô không cần khởi tạo | Thực tế dùng **Everest ES8311** kết nối I2C `0x18` | **Ảo giác nghiêm trọng**: Đã tạo driver `audio_es8311_engine.h` nạp toàn bộ 69 thanh ghi chuẩn Espressif. |
| **Amply Loa (`PA_EN`)** | Không biết có IC khuếch đại SC8002B hoặc nghĩ loa luôn bật | Thực tế có chân `PA_EN = GPIO 1`, kích hoạt ở mức **Active LOW** | **Nguyên nhân chính gây mất tiếng loa**: Nếu GPIO 1 ở mức `HIGH` hoặc thả nổi, amply bị ngắt hoàn toàn. |
| **Xung MCLK cho Audio** | Bỏ qua hoặc không cấp Master Clock | Bắt buộc phải có xung `I2S_MCLK = GPIO 4` ($4.096\text{ MHz}$) | Thiếu MCLK khiến bộ chuyển đổi DAC/ADC của ES8311 ngừng hoạt động. |
| **Chân Đèn LED RGB** | Gán nhầm chân hoặc coi là LED đơn | Sử dụng LED địa chỉ WS2812 kết nối vào **GPIO 42** | Đã cấu hình qua thư viện Adafruit NeoPixel. |
| **Âm lượng DAC ES8311** | Gán giá trị volume trực tiếp | Thanh ghi 0x32 của ES8311: `0x00 = -95.5dB`, `0xBF = 0dB`, `0xFF = +18dB` | Cần scale chính xác để âm thanh đủ to lái loa rời 8Ω qua SC8002B mà không méo tiếng. |

---

## 6. QUY TRÌNH KIỂM CHỨNG TRƯỚC KHI BÀN GIAO (VERIFICATION PROTOCOL)

Mọi thay đổi liên quan đến âm thanh hoặc firmware bắt buộc phải trải qua các bước kiểm tra thực tế:
1. **Kiểm tra biên dịch:** Không có warning nghiêm trọng, chiếm < 85% Flash và < 50% RAM.
2. **Kiểm tra trực tiếp trên cổng COM6 (Panel 2):**
   - Gửi ký tự `'d'` $\rightarrow$ In dump 69 thanh ghi ES8311, xác nhận `Reg 0x10=0x1F`, `Reg 0x11=0x7F`, `Reg 0x13=0x10`, `Reg 0x31=0x00`.
   - Gửi ký tự `'t'` $\rightarrow$ Kiểm tra âm thanh phát ra loa vật lý (Sine tone 1000Hz).
   - Gửi ký tự `'m'` $\rightarrow$ Thu âm 1.5 giây và in chỉ số RMS / Peak của Microphone.
3. **Triển khai OTA lên thiết bị thực tế:** Đẩy file `.bin` lên NAS Hub và gửi lệnh kích hoạt cập nhật đồng thời cho cả 2 Panel.

---

## 7. KIẾN TRÚC GIAO DIỆN V3.0 (4 TAB & ĐA PHÒNG LIÊN KẾT WEBSOCKET)

- **Cơ chế phân bổ 4 Tab đáy (60px/tab):**
  - Tab 0: `🏠 THIẾT BỊ` — Lưới 2 cột cuộn dọc mượt mà (chứa tối đa 16 nút, không giới hạn 4 nút như bản cũ). Tích hợp thanh lọc phòng dạng Chip và thanh cảnh báo toàn nhà có nút `[TẮT HẾT]` 1 chạm.
  - Tab 1: `🤖 TRỢ LÝ AI` — Dành trọn vẹn $240 \times 242\text{ px}$ cho hoạt ảnh AI Waveform, khung chat cuộn hiển thị câu trả lời dài từ Gemini/DeepSeek và nút PTT lớn.
  - Tab 2: `📞 ĐÀM THOẠI` — Kênh Intercom 520-byte gọi từng phòng hoặc gọi toàn nhà.
  - Tab 3: `⚙️ CÀI ĐẶT` — Chỉnh âm lượng, độ sáng, mic gain, model AI, OTA.
- **Nâng cấp WebSocket Sync:**
  - Tin nhắn `config_sync` và `house_status_update` gửi kèm trạng thái toàn bộ các phòng trong nhà.
  - Lệnh `master_turn_off_all` tắt hàng loạt thiết bị đang mở trong Home Assistant.


