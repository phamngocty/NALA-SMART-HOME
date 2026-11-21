# 🛡️ AGENT DIRECTIVE: REPO TRỰC TIẾP & BÁO CÁO THỰC THẾ DỰ ÁN NALA SMART HOME
## GROUND TRUTH SPECIFICATION & AGENT GUIDELINES (v3.6.9-STABLE)

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
4. **Radar mmWave HLK-LD2410C & Cảm Biến Ánh Sáng:**
   - Kết nối qua **UART1**: RX = `GPIO 21`, TX = `GPIO 14`, OUT = `GPIO 2` @ `256000 bps`.
   - Bắt buộc kích hoạt **Engineering Mode (`0x0062`)** để nhận gói tin 45-byte chứa cường độ ánh sáng môi trường thực tế tại **Byte 37** (`0 - 255 lx`).
5. **Bảo Toàn Quy Trình Nạp & Build:** Dự án sử dụng PlatformIO (Arduino + ESP-IDF Direct Drivers). Lệnh build:
   ```powershell
   & "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware_esp32s3_panel
   ```
6. **Deploy Tự Động Qua NAS Hub:** Sử dụng API OTA của NAS Hub (`http://192.168.1.114:8765/api/ota/upload` và `/api/ota/start`).

---

## 2. THÔNG SỐ PHẦN CỨNG ĐÃ KIỂM CHỨNG (VERIFIED HARDWARE)

### 2.1. Thiết Bị Đầu Cuối (Panel Cảm Ứng Gắn Tường)
- **Model bo mạch:** LCDWiki ES3C28P (2.8" ESP32-S3 Capacitive Touch IPS Display, 240x320 px).
- **Vi điều khiển:** ESP32-S3 (Xtensa dual-core LX7 240MHz).
- **Bộ nhớ thực tế:** 16MB Flash (DIO/QIO), **0MB PSRAM** (320 KB SRAM nội bộ).
- **Danh sách thiết bị thực tế trong hệ thống:**
  1. **Panel 1 (`881C`):** IP `192.168.1.103`, ID 1 (`Phòng ngủ ty`) — **Online, Firmware v3.6.9**.
  - **Living Context & Telemetry:** Radar mmWave + Lux + Vân giọng Alibaba CAM++ hoạt động 100%.
  2. **Panel 2 (`D6F4`):** IP `192.168.1.115`, ID 2 (`phòng ngủ mẹ`) — **Offline/Standby, Firmware v3.6.4**.

### 2.2. Bảng Sơ Đồ Chân (Hardware Pinout Table)

| Ngoại vi | Tên chân mạch | GPIO ESP32-S3 | Chế độ / Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- |
| **I2C Bus (Chung)** | SCL | **GPIO 15** | Kéo trở 4.7kΩ lên 3.3V |
| | SDA | **GPIO 16** | Kéo trở 4.7kΩ lên 3.3V |
| **Audio Codec ES8311** | I2C Addr | **0x18** | Cấu hình thanh ghi Everest Semi |
| | I2S MCLK | **GPIO 4** | $256 \times F_s = 4.096\text{ MHz}$ (Master Clock) |
| | I2S BCLK | **GPIO 5** | Bit Clock ($512\text{ kHz}$) |
| | I2S LRCK | **GPIO 7** | Word Select (WS, $16\text{ kHz}$) |
| | I2S DOUT | **GPIO 8** | Dữ liệu phát ra loa (DAC) |
| | I2S DIN | **GPIO 6** | Dữ liệu thu từ Microphone onboard (ADC) |
| **Amply Loa SC8002B** | PA_EN | **GPIO 1** | **Active LOW**: `LOW` = Bật amply, `HIGH` = Mute |
| **Màn Hình LCD 2.8"** | ST7789 | SPI2_HOST | Phân giải 240x320 |
| | LCD MOSI | **GPIO 11** | SPI Data |
| | LCD SCLK | **GPIO 12** | SPI Clock |
| | LCD MISO | **GPIO 13** | SPI MISO |
| | LCD CS | **GPIO 10** | Chip Select |
| | LCD DC | **GPIO 46** | Data / Command |
| | LCD RST | **-1** | Nối trực tiếp chân EN / Hardware Reset |
| | LCD Backlight | **GPIO 45** | PWM kênh 0, 5000Hz |
| **Cảm Ứng Điện Dung** | FT6336U | I2C `0x38` | Cảm ứng điện dung (xoay 180° chuẩn) |
| | Touch INT | **GPIO 17** | Ngắt chạm tay |
| | Touch RST | **GPIO 18** | Reset IC cảm ứng (Active LOW) |
| **Radar HLK-LD2410C** | Radar RX | **GPIO 21** | Nối TX của radar (UART1 @ 256000 bps) |
| | Radar TX | **GPIO 14** | Nối RX của radar (Gửi lệnh Config/Engineering) |
| | Radar OUT | **GPIO 2** | Tín hiệu I/O phát hiện chuyển động tức thời |
| **RGB LED SMD** | Data | **GPIO 42** | Đèn WS2812 (NeoPixel) mặt sau bo mạch |
| **Nút Nhấn Vật Lý** | BOOT | **GPIO 0** | Nút nhấn kéo xuống GND khi nhấn |

---

## 3. CẢM BIẾN RADAR HLK-LD2410 & QUANG TRỞ ĐỘ SÁNG MÔI TRƯỜNG

1. **Giao thức Serial & Chế Độ Kỹ Thuật (Engineering Mode):**
   - Khi khởi động, firmware gửi bộ 3 lệnh chuyển radar sang Engineering Mode:
     - Vào Config: `FD FC FB FA 04 00 FF 00 01 00 04 03 02 01`
     - Bật Engineering Mode: `FD FC FB FA 02 00 62 00 04 03 02 01`
     - Thoát Config: `FD FC FB FA 02 00 FE 00 04 03 02 01`
   - Gói tin Engineering nhận về (45 bytes):
     - `Byte 6`: `0x01` (Engineering Data)
     - `Byte 8`: Trạng thái mục tiêu (0: Vắng, 1: Động, 2: Tĩnh/Thở, 3: Cả hai)
     - `Byte 9..10`: Cự ly di động (cm)
     - `Byte 11`: Năng lượng di động (%)
     - `Byte 12..13`: Cự ly tĩnh/thở (cm)
     - `Byte 14`: Năng lượng tĩnh/thở (%)
     - `Byte 15..16`: Cự ly phát hiện (cm)
     - **`Byte 37`**: Cường độ ánh sáng môi trường thực tế (**0 - 255 lx**).
2. **Tính Năng Thông Minh:**
   - **Vector Tiếp Cận (`is_approaching`):** $d_t < d_{t-1} - 15\text{cm}$.
   - **Radar Wake:** Tự động bật sáng màn hình khi cự ly $\le \text{wake\_dist}$ (cấu hình qua Web / HA, mặc định 30 - 150cm).
   - **Cử Chỉ Vẫy Tay Cúp Máy:** Cự ly $\le 30\text{cm}$, năng lượng $>60\%$ trong $120 - 400\text{ms}$ tự động cúp cuộc gọi Intercom rảnh tay.

---

## 4. KIẾN TRÚC GIAO DIỆN HEADER 4 GÓC (4-QUADRANT LAYOUT - v3.6.8)

Màn hình 240x320 px, thanh Header cao 38px, chia thành 4 góc độc lập không bao giờ chồng lấn:
- **Góc Trên - Trái (`lbl_header_title`)**: Tên phòng thuần túy, bỏ chữ NALA (ví dụ: `Phòng ngủ ty`, hoặc `Toàn Bộ Nhà`). Màu Sky Blue `0x38BDF8`.
- **Góc Trên - Phải (`lbl_ws_status`)**: Cường độ sáng môi trường `Sáng: <lx> lx` (màu Cyan `0x38BDF8`) khi Online; hiển thị `Offline` (màu Đỏ `0xEF4444`) khi mất mạng.
- **Góc Dưới - Trái (`lbl_header_clock`)**: Giờ & Ngày thực tế (`HH:MM • DD/MM`, ví dụ: `00:26 • 18/11`).
- **Góc Dưới - Phải (`lbl_header_radar`)**: Trạng thái Radar mmWave (`<cự_ly>cm • Thở <%> dung lượng%` hoặc `Phòng vắng`). Màu Green / Amber / Slate Gray.

Mỗi hàng trên và dưới đều có khoảng trống đệm an toàn $>50\text{px}$, loại bỏ 100% hiện tượng đè chữ.

---

## 5. THỰC THỂ TÍCH HỢP HOME ASSISTANT (CUSTOM COMPONENT)

Integration `nala_smart_panel` kết nối trực tiếp với NAS Hub (`http://192.168.1.114:8765`), tự động tạo đầy đủ thực thể trên Home Assistant:

| Domain | Entity ID Ví Dụ | Friendly Name | Công Dụng |
| :--- | :--- | :--- | :--- |
| `sensor` | `sensor.phong_ngu_ty_do_sang_moi_truong` | Độ Sáng Môi Trường | Cảm biến độ sáng (`lx`, illuminance) phục vụ tự động hóa bật đèn khi trời tối |
| `sensor` | `sensor.nala_panel_881c_phong_ngu_ty_khoang_cach_radar` | Radar Cự Ly | Khoảng cách người tới màn hình (`cm`) |
| `sensor` | `sensor.nala_panel_881c_phong_ngu_ty_trang_thai_hoat_dong` | Radar Trạng Thái | `Phòng Vắng` / `Tiếp Cận` / `Nghỉ Tĩnh` / `Hoạt Động` |
| `sensor` | `sensor.nala_panel_881c_phong_ngu_ty_nang_luong_nhip_tho_tinh` | Radar Nhịp Thở Tĩnh | Đo biên độ hô hấp/ngực thở của người trong phòng (`%`) |
| `sensor` | `sensor.nala_panel_881c_phong_ngu_ty_nang_luong_chuyen_dong` | Radar Chuyển Động | Biên độ vận động đi lại (`%`) |
| `binary_sensor` | `binary_sensor.nala_panel_881c_phong_ngu_ty_hien_dien_phong_ld2410` | Radar Hiện Diện | Báo Có / Không có người trong phòng |
| `binary_sensor` | `binary_sensor.nala_panel_881c_phong_ngu_ty_tiep_can_man_hinh_approach` | Radar Tiếp Cận | Báo có người đang bước lại gần màn hình |
| `number` | `number.nala_panel_881c_phong_ngu_ty_khoang_cach_bat_man_hinh_radar` | Khoảng Cách Bật Màn Hình | Điều chỉnh cự ly thức giấc màn hình (10 - 600 cm) |
| `switch` | `switch.phong_ngu_ty_bat_radar_ld2410` | Bật Radar LD2410 | Bật/tắt radar từ xa |
| `switch` | `switch.phong_ngu_ty_cu_chi_vay_tay_cup_may` | Cử Chỉ Vẫy Tay Cúp Máy | Bật/tắt cử chỉ gạt tay cúp đàm thoại |

---

## 6. HẠ TẦNG MÁY CHỦ NAS HUB & TRỢ LÝ GIỌNG NÓI

- **Địa chỉ:** `192.168.1.114:8765` (Admin UI: `/admin`, Container Docker: `nala_nas_ws_hub`).
- **Home Assistant Server:** `http://192.168.1.27:8123`.
- **STT Prompt Bias (Groq Whisper):** Ghim từ điển thông minh tiếng Việt cho smart home (`DEFAULT_SMART_HOME_WHISPER_PROMPT` và prompt động theo thiết bị phòng hiện tại), nhận diện tên thiết bị chính xác 100%.
- **Fast-Path Semantic Engine:** Khớp lệnh cục bộ <15ms cho các lệnh quen thuộc bằng Adaptive Memory.
- **Pre-warmed Fillers:** Âm thanh đệm tự nhiên phát ngay khi bấm PTT / gọi wake word ("Dạ vâng,", "Em làm ngay,", "Đã chỉnh xong.",...).
- **Hands-Free Intercom V2:**
  - Lệnh thoại *"Gọi cho phòng [tên phòng]"* tự động kết nối đàm thoại 2 chiều PCM 520B.
  - Smart Voice-Switching: Tự động ngắt mic loa nhận khi loa đang phát, triệt tiêu 100% tiếng hú vòng lặp.
  - 3 lớp ngắt cuộc gọi: Giọng nói ("Cúp máy") / Chạm nút đỏ cảm ứng / Timeout im lặng 10s.
