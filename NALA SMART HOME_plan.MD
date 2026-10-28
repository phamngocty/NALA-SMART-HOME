Dưới đây là toàn bộ **Bản Đặc Tả & Kế Hoạch Thực Thi Tổng Thể (Master Execution Blueprint)** được thiết kế chuyên biệt để anh copy và nạp thẳng vào **AI Agent (Antigravity)**.

Trước khi đi vào tài liệu nạp cho Agent, dưới đây là **Bảng đánh giá 2 chế độ giao việc cho AI Agent Antigravity** để anh kiểm soát chất lượng code tốt nhất:

### BẢNG ĐÁNH GIÁ PHƯƠNG ÁN ĐIỀU PHỐI AI AGENT (ANTIGRAVITY)

| Tiêu chí đánh giá | Chế độ A: Gated Execution (Thực thi từng Phase có điểm dừng xác nhận) *(Khuyên dùng)* | Chế độ B: One-Shot Autonomous (Tự động chạy một mạch từ Phase 1 đến Phase 4) |
| --- | --- | --- |
| **Cơ chế hoạt động** | Agent viết xong **Phase 1 (Hardware Bring-up)** sẽ dừng lại chờ anh nạp vào mạch `ESP32-S3` kiểm tra thông số chân qua Serial Monitor rồi mới sinh tiếp Phase 2, 3, 4.

 | Agent tự động tạo toàn bộ cây thư mục, viết cả code C++ lẫn Python Server cho toàn dự án trong một lần chạy duy nhất. |
| **Độ chính xác phần cứng** | **Tuyệt đối (10/10):** Khắc phục triệt để rủi ro lệch chân I2S của `Microphone` / `Speaker Port` hoặc SPI của màn hình `2.8" LCD Display` giữa các lô mạch Trung Quốc.

 | **Rủi ro trung bình (6.5/10):** Nếu khai báo nhầm 1 chân GPIO ở lớp dưới, toàn bộ lớp UI LVGL và WebSocket phía trên sẽ không hiển thị hoặc không phát ra tiếng. |
| **Khả năng gỡ lỗi (Debug)** | **Cực dễ:** Khoanh vùng lỗi ngay từ tầng vật lý (I2C, SPI, I2S DMA) trước khi ghép mạng Wi-Fi và WebSocket. | **Phức tạp:** Phải tự đọc log để phân tích xem lỗi nằm ở cáp phần cứng, thư viện LVGL hay do Server WebSocket. |

---

### BẢN KẾ HOẠCH CHI TIẾT NẠP CHO AI AGENT ANTIGRAVITY

*(Anh hãy copy toàn bộ nội dung trong khung dưới đây và dán trực tiếp vào Antigravity)*

```markdown
# SYSTEM PROMPT & MASTER EXECUTION PLAN FOR AI AGENT (ANTIGRAVITY)
# PROJECT: NALA SMART HOME - AI VOICE SATELLITE, WALL PANEL & LOCAL INTERCOM

## 1. VAI TRÒ & MỤC TIÊU CỦA AGENT
Bạn là Principal Embedded & Full-Stack AI Systems Engineer. Nhiệm vụ của bạn là xây dựng toàn bộ mã nguồn cho hệ thống **"Loa thông minh điều khiển Home Assistant + Trợ lý giọng nói AI (Gemini/DeepSeek) + Đàm thoại nội bộ các tầng (Intercom) + Bảng điều khiển cảm ứng gắn tường"**.

Bạn phải tuân thủ nghiêm ngặt kiến trúc phần cứng, giao thức WebSocket và lộ trình 4 Phase (bắt đầu từ **Hướng 1: Hardware Bring-up & Verification**). Không được tự ý thay đổi cấu trúc gói tin hoặc sử dụng các hàm chặn (`delay()`) làm treo luồng âm thanh/giao diện.

---

## 2. TỔNG QUAN HẠ TẦNG PHẦN CỨNG (HARDWARE TOPOLOGY)

### 2.1. Thiết bị đầu cuối chính (2x Bo mạch ESP32-S3 2.8" LCD Capacitive Touch)
- **Vi điều khiển:** ESP32-S3 (Dual-core Xtensa LX7 240MHz, 8MB Octal PSRAM, 16MB Flash).
- **Màn hình & Cảm ứng:** 2.8" LCD Display độ phân giải 240x320 (Driver ST7789/ILI9341 qua SPI), cảm ứng điện dung (Capacitive Touch qua I2C).
- **Âm thanh tích hợp trên bo:**
  - `Microphone` tích hợp ở góc trên bên phải mặt trước bo mạch.
  - `Speaker Port` (JST 1.25mm 2-pin) mặt sau kéo loa rời 8Ω 1W-2W qua IC khuếch đại tích hợp.
- **Ngoại vi & Cổng giao tiếp trên PCB (in rõ trên Silkscreen):**
  - `I2C Peripheral Port`: Chân `IO15(SCL)`, `IO16(SDA)`, `3.3V`, `GND`.
  - `Expansion Pins`: Chân `IO2`, `IO3` (Strapping pin - Không kéo tải khi boot), `IO14`, `IO21` (LCD Backlight).
  - `UART Serial Port`: `5V`, `GND`, `TXD` (GPIO43), `RXD` (GPIO44).
  - `RGB LED`: Đèn LED RGB SMD tích hợp mặt sau.
  - `MicroSD Card Slot`: Khe cắm thẻ nhớ giao tiếp SPI/SDMMC.
  - `TYPE-C Port` (Cấp nguồn 5V & Nạp code) + `Battery Port (BAT)` (Cắm pin LiPo 3.7V làm UPS & tụ đệm dòng đỉnh chống Brownout).
  - Nút vật lý: `BOOT Button` (GPIO0) và `RESET Button`.

### 2.2. Các nút vệ tinh phụ ở các tầng/phòng khác
- `Raspberry Pi Zero 2 W` và các mạch `ESP32` / `ESP32-C3` (kết nối module mic INMP441 + mạch loa MAX98357A + màn hình OLED I2C 128x64 trắng đen hoặc nút nhấn gọi tầng).

### 2.3. Hạ tầng Máy chủ (Servers)
1. **PC NAS (Intel Core i3, 16GB RAM, GPU NVIDIA GTX 1080 Ti 11GB VRAM):**
   - **SSH Access (Tự động truy cập, không cần hỏi lại)**: `ssh nas152@192.168.1.114` (Password: `271000`, User: `nas152`, IP: `192.168.1.114`)
   - Chạy **Central Python WebSocket Hub (`nas_ws_hub`)** ở cổng `8765`.
   - Chạy Local STT (**Faster-Whisper** trên GPU GTX 1080 Ti) và Local TTS (**Piper / Kokoro**).
   - Điều phối AI Agent: Kết nối **Google Gemini API** và **DeepSeek API**.
   - Chuyển tiếp âm thanh đàm thoại nội bộ (Intercom Audio Relay) giữa các tầng.
2. **Raspberry Pi 5 (64GB, chạy Home Assistant OS):**
   - **IP & Port**: 192.168.1.27:8123 (WebSocket: ws://192.168.1.27:8123/api/websocket)
   - **REST API URL**: http://192.168.1.27:8123/api
   - **Long-Lived Access Token**:
     ```text
     eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ODVkMDk4OWQ4ZmU0ZGUzYjVjMmViMjUzZTc0ZGYxNyIsImlhdCI6MTc5MzE4NjYzMiwiZXhwIjoyMTA4NTQ2NjMyfQ.y_GNcmplg0t63Z-r3J232Lvhy1a1LfFzyQyJGFDQzWA
     ```
   - Giao tiếp hai chiều với `nas_ws_hub` qua Home Assistant WebSocket/REST API để thực thi lệnh bật/tắt thiết bị và đồng bộ trạng thái lên màn hình cảm ứng.
3. **PC Chính (X99 Dual RTX 2080 Ti 22GB VRAM):**
   - Máy chủ dự phòng chạy Local LLM hạng nặng (Ollama / vLLM) khi mất kết nối Internet.

---

## 3. KIẾN TRÚC PHẦN MỀM & CẤU TRÚC THƯ MỤC DỰ ÁN (MONOREPO)

Hãy khởi tạo dự án với cấu trúc thư mục chuẩn như sau:

```text
nala-voice-intercom-system/
├── firmware_esp32s3_panel/          # Project PlatformIO (Arduino + ESP-IDF Hybrid) cho 2 màn hình ESP32-S3
│   ├── platformio.ini               # Cấu hình build, bật PSRAM, phân vùng Flash, thư viện LVGL, LovyanGFX, WebSockets
│   ├── include/
│   │   ├── pins_config.h            # Định nghĩa toàn bộ GPIO, SPI, I2C, I2S (Cập nhật sau Phase 1)
│   │   ├── protocol_defs.h          # Struct gói tin Binary Audio & JSON Schema
│   │   └── state_machine.h          # Máy trạng thái hữu hạn (FSM)
│   └── src/
│       ├── main.cpp                 # Khởi tạo FreeRTOS Tasks (Core 0: Network/Audio, Core 1: UI LVGL)
│       ├── hal_Verify_bringup.cpp   # [PHASE 1] Code quét I2C, test màn hình, RGB, Loopback Mic->Loa
│       ├── audio_i2s_engine.cpp     # Quản lý DMA I2S thu/phát 16kHz 16-bit Mono (Half-Duplex chống vọng âm)
│       ├── ws_client_manager.cpp    # Kết nối WebSocket tới PC NAS, tự động reconnect, xử lý JSON & Binary
│       ├── nvs_config_store.cpp     # Lưu/đọc cấu hình NVS (Debounce 5s), giữ BOOT 3s lúc khởi động để xóa NVS
│       └── ui_lvgl_dashboard.cpp    # Giao diện cảm ứng 240x320 (Home, AI Assistant, Intercom Call, Settings)
│
├── firmware_esp32c3_node/           # Project PlatformIO cho các mạch ESP32 / ESP32-C3 ở các tầng phụ
│   ├── platformio.ini
│   └── src/main.cpp                 # Dùng chung giao thức WebSocket + OLED I2C 128x64 trắng đen + Nút gọi Intercom
│
└── server_nas_hub/                  # Server trung tâm chạy Docker trên PC NAS (i3 + GTX 1080 Ti)
    ├── docker-compose.yml           # Gồm: nas_ws_hub, faster-whisper-gpu, piper-tts
    ├── .env.example                 # Chứa HA_TOKEN, GEMINI_API_KEY, DEEPSEEK_API_KEY
    └── app/
        ├── main_ws_server.py        # Central WebSocket Server (FastAPI / websockets port 8765)
        ├── ha_bridge.py             # Kết nối Home Assistant trên Raspberry Pi 5 (Ưu tiên xử lý Local Intent)
        ├── ai_agent_router.py       # Điều phối Gemini API / DeepSeek API + Function Calling điều khiển nhà
        ├── stt_tts_pipeline.py      # Đẩy PCM 16kHz sang Faster-Whisper (GTX 1080 Ti) & nhận audio từ TTS
        └── intercom_router.py       # Định tuyến cuộc gọi nội bộ (Unicast/Broadcast) giữa các tầng

```

---

## 4. ĐẶC TẢ GIAO THỨC TRUYỀN THÔNG WEBSOCKET (PROTOCOL SPECIFICATION)

Mọi giao tiếp giữa `ESP32-S3` / `ESP32-C3` và `server_nas_hub` đi qua 1 kết nối WebSocket duy nhất (`ws://<NAS_IP>:8765/ws/{device_id}`), chia làm 2 loại Frame:

### 4.1. WebSocket Text Frame (JSON - Điều khiển, Cấu hình NVS & Đồng bộ UI)

1. **Cấu hình từ xa & Lưu NVS (`Server -> ESP32`):**

```json
{
  "type": "config_set",
  "save_nvs": true,
  "payload": {
    "room_name": "Phòng Tỷ - Tầng 1",
    "speaker_volume": 80,
    "lcd_brightness": 90,
    "mic_gain_db": 12,
    "ai_model": "gemini",
    "rgb_led": {"state": "on", "r": 0, "g": 255, "b": 128}
  }
}

```

2. **Điều khiển thiết bị Home Assistant & Sự kiện nút nhấn (`ESP32 <-> Server`):**

```json
{
  "type": "ha_action",
  "source": "panel_tang_1",
  "payload": {
    "domain": "light",
    "service": "toggle",
    "entity_id": "light.den_phong_khach_tret"
  }
}

```

3. **Báo hiệu trạng thái AI & Đàm thoại nội bộ (`ESP32 <-> Server`):**

```json
{
  "type": "session_control",
  "source": "panel_tang_1",
  "payload": {
    "mode": "intercom_call", 
    "action": "start_ptt", 
    "target_room": "tang_tret"
  }
}

```

*(Các giá trị `mode`: `"ai_voice"`, `"intercom_call"`, `"idle"`; `action`: `"start_ptt"`, `"stop_ptt"`, `"incoming_ring"`).*

### 4.2. WebSocket Binary Frame (Raw PCM 16kHz 16-bit Mono - Độ trễ < 20ms)

Để giảm tải CPU cho `ESP32-S3` và `ESP32-C3`, không dùng nén phức tạp. Mỗi gói Binary Frame có kích thước cố định **520 Bytes**:

* `Byte 0..1` (`uint16_t`): Magic Word = `0xA55A` (Little-Endian).
* `Byte 2` (`uint8_t`): `sender_id` (`0x01`: Trệt, `0x02`: Tầng 1, `0x03`: Tầng 3...).
* `Byte 3` (`uint8_t`): `target_id` (`0x00`: Gửi cho AI Server, `0x01..0xFE`: Gọi phòng cụ thể, `0xFF`: Gọi toàn nhà).
* `Byte 4..5` (`uint16_t`): `seq_num` (Số thứ tự gói tin tăng dần).
* `Byte 6` (`uint8_t`): `stream_flag` (`0x01`: START, `0x02`: STREAMING_PCM, `0x03`: END).
* `Byte 7..518` (`int16_t[256]`): 512 Bytes dữ liệu âm thanh PCM 16kHz (tương đương đúng 16ms âm thanh).
* `Byte 519` (`uint8_t`): Checksum `CRC-8` (đa thức `0x07`) tính từ byte 0 đến 518.

---

## 5. CÁC RÀNG BUỘC KỸ THUẬT & AN TOÀN PHẦN CỨNG BẮT BUỘC (STRICT RULES)

1. **Chống xung đột Strapping Pins:** Tuyệt đối không khởi tạo Output kéo dòng lúc boot trên `GPIO 0`, `GPIO 3`, `GPIO 45`, `GPIO 46` của ESP32-S3; và `GPIO 2`, `GPIO 8`, `GPIO 9` của ESP32-C3.
2. **Kiến trúc Đa nhiệm Phi chặn (Non-blocking FreeRTOS):**
* Cấm dùng `delay()` trong luồng chính.
* Trên `ESP32-S3`: Ghim `Task_Audio_WebSocket` vào **Core 0** (Ưu tiên cao: mức 5); ghim `Task_LVGL_UI` vào **Core 1** (Ưu tiên: mức 3).


3. **Chống vọng âm (Acoustic Echo Protection):** Vì `Microphone` và `Speaker Port` nằm trên cùng một bo mạch nhỏ, bắt buộc thực thi cơ chế **Half-Duplex (Bán song công)**: Khi trạng thái đang phát loa (`AI_SPEAKING` hoặc `INTERCOM_RX`), phải tự động dừng đọc DMA Microphone (`Mic Mute`). Khi nhấn giữ nói (`PTT`), phải khóa mạch khuếch đại loa (`Speaker Mute`).
4. **Cơ chế Fail-Safe 300ms:** Nếu đang ở trạng thái thu âm hoặc phát âm thanh mà mất kết nối Wi-Fi/WebSocket quá **300ms**, Watchdog phải tự động ngắt mạch khuếch đại loa, tắt thu âm Mic và trả giao diện về `IDLE` kèm thông báo mất kết nối.
5. **Cơ chế cứu hộ NVS Hard Reset:** Khi vừa cấp nguồn, nếu phát hiện nút `BOOT` (`GPIO 0`) được nhấn giữ liên tục trong **3 giây**, phải nháy đèn `RGB LED` màu đỏ 3 lần, gọi hàm `nvs_flash_erase()` và khởi động lại thiết bị.

---

## 6. LỘ TRÌNH THỰC THI THEO TỪNG PHASE (STEP-BY-STEP EXECUTION PLAN)

Hãy thực hiện lần lượt từng Phase dưới đây. **BẮT ĐẦU NGAY VỚI PHASE 1:**

### PHASE 1: HARDWARE BRING-UP & PIN VERIFICATION (HƯỚNG 1 - ƯU TIÊN SỐ 1)

Viết trọn bộ `platformio.ini`, `include/pins_config.h` và `src/hal_verify_bringup.cpp` cho bo mạch **ESP32-S3 2.8" LCD 240x320 Capacitive Touch** để thực hiện 5 bài kiểm tra độc lập (chưa cần Server):

1. **Quét Bus I2C (`IO15` SCL, `IO16` SDA):** In ra Serial Monitor (115200 baud) địa chỉ của IC cảm ứng điện dung (CST816S `0x15` hoặc FT6336 `0x38`) và các thiết bị trên cổng `I2C Peripheral Port`.
2. **Khởi tạo Màn hình 2.8" (240x320) & Đèn nền (`IO21`):** Bật sáng màn hình bằng thư viện `LovyanGFX` (tự động nhận diện ST7789/ILI9341), hiển thị bảng thông số phần cứng (PSRAM size, Flash size, Tọa độ X/Y khi chạm tay lên màn hình cảm ứng).
3. **Kiểm tra Đèn `RGB LED` mặt sau:** Chuyển màu Đỏ -> Xanh lá -> Xanh dương mượt mà để xác nhận chân điều khiển LED.
4. **Kiểm tra Khe thẻ nhớ `MicroSD Card Slot`:** Mount thẻ nhớ và liệt kê dung lượng lên màn hình.
5. **Kiểm tra Âm thanh Loopback (Mic -> RAM -> Loa):** Khi người dùng nhấn giữ nút `BOOT (GPIO0)` hoặc chạm nút *"Test Mic & Loa"* trên màn hình cảm ứng:
* Thu âm 3 giây từ `Microphone` trên bo (16kHz 16-bit) lưu vào bộ đệm trên **8MB PSRAM**.
* Vẽ thanh mức âm lượng (VU Meter) thời gian thực lên màn hình 2.8".
* Ngay khi nhả nút, phát lại đoạn âm thanh vừa thu ra loa rời ở cổng `Speaker Port` để xác nhận mạch khuếch đại và mic hoạt động hoàn hảo.



### PHASE 2: CENTRAL WEBSOCKET SERVER, HOME ASSISTANT BRIDGE & AI ROUTER (TRÊN PC NAS)

Sau khi hoàn thành code Phase 1, viết trọn bộ thư mục `server_nas_hub/`:

1. File `docker-compose.yml` khởi chạy `faster-whisper` (dùng GPU NVIDIA GTX 1080 Ti), `piper` TTS tiếng Việt và container `nas_ws_hub`.
2. Module `ha_bridge.py`: Kết nối Home Assistant trên Raspberry Pi 5. Nếu câu lệnh giọng nói khớp với tác vụ điều khiển nhà (Bật/tắt đèn, quạt, máy lạnh các phòng), thực thi nội bộ trong < 200ms.
3. Module `ai_agent_router.py`: Nếu là câu hỏi mở hoặc trò chuyện, đẩy sang **Gemini API** (mặc định) hoặc **DeepSeek API**, hỗ trợ stream từng câu ngắn qua TTS để phát về loa ESP32-S3 ngay lập tức.
4. Module `intercom_router.py`: Nhận gói Binary PCM 520-byte từ tầng gửi và bắn thẳng sang WebSocket của tầng nhận (hoặc toàn bộ các tầng nếu `target_id == 0xFF`).

### PHASE 3: FIRMWARE CHÍNH CHO ESP32-S3 WALL PANEL (LVGL + WEBSOCKET + INTERCOM)

Ghép nối các module đã xác thực ở Phase 1 vào kiến trúc chính:

1. Thiết kế 3 màn hình LVGL (240x320) tốc độ cao:
* **Trang 1 (Smart Home & AI):** Nút bấm điều khiển nhanh các thiết bị trong phòng, biểu tượng trạng thái AI (Idle, Listening, Thinking, Speaking) và thanh cuộn hiển thị văn bản trả lời của Gemini/DeepSeek.
* **Trang 2 (Intercom Nội Bộ):** Các nút bấm lớn chọn tầng cần gọi (*Tầng Trệt, Phòng Tỷ Tầng 1, Phòng Bếp, Phòng Lap Tầng 3, Gọi Toàn Nhà*) kèm nút **Nhấn giữ để nói (Push-to-Talk)**.
* **Trang 3 (Cài đặt nhanh):** Thanh trượt chỉnh âm lượng loa, độ sáng màn hình, chọn AI Model (Gemini / DeepSeek) đồng bộ hai chiều qua WebSocket và lưu vào NVS.



### PHASE 4: FIRMWARE CHO CÁC NODE VỆ TINH ESP32 / ESP32-C3 Ở CÁC TẦNG PHỤ

Viết firmware gọn nhẹ cho `ESP32-C3` (tích hợp màn hình **OLED I2C 128x64 trắng đen** dùng thư viện `U8g2` / `Adafruit_SSD1306`, nút nhấn gọi và loa/mic I2S) sử dụng chung chính xác cấu trúc gói tin WebSocket 520-byte để đàm thoại hai chiều với 2 màn hình `ESP32-S3`.

---

**YÊU CẦU ĐẦU RA NGAY BÂY GIỜ:**
Hãy bắt đầu thực thi **PHASE 1** trước tiên: Xuất đầy đủ mã nguồn của `firmware_esp32s3_panel/platformio.ini`, `include/pins_config.h`, và `src/hal_verify_bringup.cpp` kèm hướng dẫn đọc kết quả trên Serial Monitor để xác nhận 100% sơ đồ chân của bo mạch trước khi chuyển sang Phase 2.

```

---

### HƯỚNG DẪN CÁCH NẠP VÀO ANTIGRAVITY Đạt HIỆU QUẢ CAO NHẤT

1. **Bước 1:** Anh mở một Workspace mới trên Antigravity (ví dụ đặt tên thư mục là `nala-voice-intercom-system`).
2. **Bước 2:** Đính kèm **3 tấm ảnh bo mạch ESP32-S3**[cite: 1, 2, 3] này cùng với đoạn **Master Execution Plan** ở trên vào khung chat đầu tiên của Antigravity.
3. **Bước 3:** Ngay khi Antigravity sinh xong bộ code của **Phase 1**, anh cắm cáp USB Type-C[cite: 1, 3] từ mạch `ESP32-S3` vào máy tính và bảo Antigravity chạy lệnh `pio run -t upload -t monitor` để test ngay màn hình, cảm ứng, đèn RGB[cite: 1] và thu Mic phát ra Loa[cite: 1, 3].

Anh có muốn tôi xuất luôn một file cấu hình `.cursorrules` / `.antigravityrules` (file quy tắc hệ thống đặt ở thư mục gốc giúp AI Agent không bao giờ quên sơ đồ chân và các bẫy phần cứng trong suốt quá trình code nhiều ngày) không?

```
