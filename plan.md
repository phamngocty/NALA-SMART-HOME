# NALA SMART HOME - Master Implementation Plan
## Kế hoạch phát triển Hệ thống Màn hình Thông minh Gắn Tường & Trợ lý Giọng nói AI Đàm thoại Nội bộ

> **Mục tiêu**: Xây dựng hệ thống màn hình cảm ứng gắn tường hoàn chỉnh chuẩn công nghiệp:
> 1. Tự phát AP `192.168.4.1` (Captive Portal) cấu hình WiFi nhà khi chưa kết nối; lưu cấu hình NVS an toàn.
> 2. Hiển thị mã ghép nối (Pairing Code) và quản lý tập trung từ Web Server trên NAS (`http://192.168.1.114:8765`).
> 3. Cấu hình tên phòng, vị trí tầng và danh sách thiết bị Home Assistant điều khiển trực tiếp qua WebSocket hai chiều.
> 4. Trò chuyện giọng nói tiếng Việt thông minh tương tự Xiaozhi AI (Faster-Whisper GPU + Gemini/DeepSeek + Piper TTS).
> 5. Đàm thoại nội bộ liên tầng (Intercom Push-to-Talk) độ trễ cực thấp (<20ms) qua luồng Raw PCM 16kHz.

---

## 1. Thông Tin Hạ Tầng & Kết Nối Thực Tế (Credentials & Infrastructure)
> **Quy ước tự động hóa (Autonomous Access Policy)**: AI / Agent được cấp quyền tự động kết nối SSH và quản lý Server NAS mà **không cần hỏi lại** thông tin hay xin xác nhận từ người dùng.

### 1.1. Server Trung Tâm NAS (Docker Host & AI Hub)
- **Host / IP**: `192.168.1.114`
- **SSH User**: `nas152`
- **SSH Password**: `271000`
- **Lệnh kết nối nhanh**: `ssh nas152@192.168.1.114` (Password: `271000`)
- **Cổng Web Hub & WebSocket**: `http://192.168.1.114:8765`
- **Phần cứng**: Intel Core i3, 16GB RAM, GPU NVIDIA GTX 1080 Ti (11GB VRAM, Pascal Compute Capability 6.1).
- **Quyền hạn tự động**: Tự động build image, chạy `docker-compose`, cấu hình container, kiểm tra log và cập nhật script qua SSH.

### 1.2. Máy Chủ Nhà Thông Minh Home Assistant (Raspberry Pi 5)
- **Host / IP**: `192.168.1.27:8123`
- **WebSocket URL**: `ws://192.168.1.27:8123/api/websocket`
- **REST API URL**: `http://192.168.1.27:8123/api`
- **Long-Lived Access Token**:
  ```text
  eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI2ODVkMDk4OWQ4ZmU0ZGUzYjVjMmViMjUzZTc0ZGYxNyIsImlhdCI6MTc5MzE4NjYzMiwiZXhwIjoyMTA4NTQ2NjMyfQ.y_GNcmplg0t63Z-r3J232Lvhy1a1LfFzyQyJGFDQzWA
  ```
- **File lưu trữ môi trường**: Đã lưu tại [server_nas_hub/.env](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/.env).

### 1.3. Trợ Lý AI (Gemini & DeepSeek Routing)
- **Cơ chế nạp API Key**: Nhập và cập nhật động từ xa thông qua Web Hub Management Dashboard (`/static/index.html`) hoặc gói tin WebSocket JSON `config_set` mà không cần biên dịch lại code.
- **Thứ tự ưu tiên (Priority Fallback)**: Cho phép người dùng chuyển đổi ưu tiên:
  - `gemini` (mặc định): Tốc độ phản hồi nhanh, xử lý function calling tốt.
  - `deepseek`: Suy luận tiếng Việt sắc bén, dùng khi chuyển chế độ hoặc làm dự phòng (fallback).

---

## 2. Triết Lý Thiết Kế & Kế Thừa Tinh Hoa Mã Nguồn Mở (Phương Án A: Clean Architecture)
Hệ thống phát triển theo **Phương án A: Khung Clean Architecture riêng biệt trên PlatformIO (Arduino + ESP-IDF)**, chắt lọc tinh hoa từ 3 dự án mã nguồn mở hàng đầu:

1. **Từ `atomic14/esp32-walkie-talkie` (Audio Engine & Đàm thoại nội bộ)**:
   - Thu/phát âm thanh I2S DMA hoàn toàn bằng FreeRTOS Task phi chặn (`audio_es8311_engine.h`).
   - Luồng Raw PCM 16kHz 16-bit Mono truyền qua WebSocket trong mạng LAN: độ trễ < 20ms, tải CPU < 5%, không tốn tài nguyên nén Opus.
   - Cơ chế Half-Duplex (PTT) ngăn chặn triệt để phản xạ âm (hú rít) giữa Mic và Loa trên cùng một bo mạch.

2. **Từ `78/xiaozhi-esp32` & `xiaozhi-esp32-server` (Voice AI & Điều phối WebSocket)**:
   - Máy trạng thái hữu hạn FSM chuẩn xác (`state_machine.h`): `IDLE` ➔ `LISTENING` ➔ `THINKING` ➔ `SPEAKING` ➔ `INTERCOM`.
   - Phân tách rõ ràng 2 kênh dữ liệu: Binary Frame cho Audio PCM và Text Frame cho JSON điều khiển/sự kiện.
   - Server Python NAS Hub (`server_nas_hub/`): Pipeline STT Faster-Whisper (GPU 1080 Ti) + AI Agent Router (Gemini/DeepSeek) + Piper TTS + Home Assistant WebSocket Bridge.

3. **Từ `HASwitchPlate/openHASP` (Màn hình gắn tường & Cấu hình giao diện động)**:
   - Áp dụng **Phương án 2: Kích hoạt LVGL 8.3.11 chuẩn**, kết hợp lớp driver tốc độ cao LovyanGFX.
   - Phản chiếu trạng thái thực thể Home Assistant và cập nhật layout nút bấm qua JSON động (`config_sync`, `state_changed`) mà không cần nạp lại firmware.

---

## 3. Kiến Trúc Giao Diện: Kích Hoạt LVGL 8.3.11 Chuẩn (Phương Án 2)
Người dùng đã chốt chọn **Phương án 2 (Kích hoạt LVGL 8.3.11 chuẩn)** để đạt trải nghiệm giao diện cao cấp:

```mermaid
graph TD
    subgraph HardwareLayer["Phần cứng ES3C28P"]
        LCD["ST7789/ILI9341 2.8' SPI (240x320)"]
        Touch["FT6336G Capacitive Touch I2C"]
        Audio["ES8311 I2S DMA Codec + Loa FM8002E"]
    end

    subgraph DriverLayer["Tầng Driver Phần Cứng (Core 1)"]
        LGFX["LovyanGFX Hardware Driver (40MHz SPI)"]
        LGFX_Touch["FT6336G Driver (Đã hiệu chuẩn đảo 180° X/Y)"]
    end

    subgraph LVGLLayer["Tầng Giao Diện Đồ Họa (LVGL 8.3.11)"]
        LV_Buf["Double Buffer (2x 240x40 dòng trong Internal SRAM)"]
        LV_Widgets["TabView, Rounded Buttons, Sliders, Switches, Textarea Stream AI"]
        LV_Theme["Nala Dark Modern Theme (Glassmorphism, mượt 60 FPS)"]
    end

    subgraph RTOSLayer["Phân Chia Đa Nhiệm FreeRTOS"]
        Core0["Core 0 (Mức 5): Task_Network_Audio (WiFi, WebSocket, I2S DMA)"]
        Core1["Core 1 (Mức 3): Task_LVGL_UI (lv_timer_handler 15ms)"]
    end

    HardwareLayer --> DriverLayer
    DriverLayer --> LVGLLayer
    LVGLLayer --> RTOSLayer
```

### Chiến Lược Quản Lý Bộ Nhớ Chống Tranh Chấp (Anti-Crash Memory Strategy)
- **Phân bổ Buffer**: Cấp phát 2 bộ đệm render LVGL nhỏ gọn (mỗi bộ 240x40 pixel = ~19.2 KB) nằm hoàn toàn trong **Internal SRAM tốc độ cao**, dành trọn **8MB Octal PSRAM** cho bộ đệm âm thanh DMA, RingBuffer gói tin WebSocket và NVS Cache.
- **Tách Lõi Độc Lập**: Ghim vòng lặp `lv_timer_handler()` vào **Core 1**; ghim toàn bộ luồng thu mic / phát loa và gửi nhận WebSocket vào **Core 0**. Khóa mutex FreeRTOS bảo vệ mọi biến dùng chung giữa 2 core.

---

## 4. Phương Án Xử Lý Triệt Để Các Điểm Bất Cập Kỹ Thuật

| Vấn đề phát hiện | Rủi ro nếu không xử lý | Giải pháp kỹ thuật triển khai |
| :--- | :--- | :--- |
| **1. Piper TTS trong `docker-compose`** | Image `rhasspy/wyoming-piper` dùng Wyoming raw TCP port 10200, trong khi Python code gọi HTTP GET `/api/tts` $\rightarrow$ lỗi 404/Connection Refused. | **Thay thế container Piper bằng HTTP TTS Service** (hoặc tích hợp client Wyoming trực tiếp trong `stt_tts_pipeline.py`) xuất trực tiếp stream WAV PCM 16kHz tiếng Việt. |
| **2. GPU GTX 1080 Ti (Pascal Compute 6.1)** | Image `faster-whisper-server:latest-cuda` có thể thiếu thư viện build cho Pascal `sm_61`; model `large-v3` chiếm ~10GB VRAM dễ tràn bộ nhớ. | Cấu hình model mặc định: `whisper-medium` (hoặc `small`), compute type `float16`, VRAM chỉ chiếm ~2.5GB, tốc độ STT nhanh gấp 3 lần (<300ms) và cực mát máy. |
| **3. Luồng Đàm Thoại PTT trên ESP32** | Chạm nút PTT trên màn hình mới chỉ đổi chữ UI, chưa kích hoạt Task đọc DMA từ mic ES8311 để bắn binary 520 byte. | Nối sự kiện touch PTT vào FreeRTOS task đọc DMA: Khi nhấn giữ PTT $\rightarrow$ Mic ON, Loa MUTE, stream 520-byte PCM; khi nhả $\rightarrow$ Mic MUTE, Loa ON. |
| **4. Tiếng nổ loa (POP Noise) lúc khởi động** | Chân `PA_EN` (GPIO 1) nếu không giữ HIGH ngay khi cấp nguồn sẽ gây nổ loa "lụp bụp". | Cấu hình `pinMode(PA_EN_PIN, OUTPUT); digitalWrite(PA_EN_PIN, HIGH);` ngay dòng đầu tiên của `setup()` trước khi khởi tạo bất kỳ ngoại vi nào. |

---

## 5. Danh Sách Các Hạng Mục Triển Khai (Task Breakdown)

### Phase 1: Chuẩn Hóa Hạ Tầng Server NAS & Docker Hub
- [x] Tạo file môi trường [.env](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/.env) với IP Home Assistant `192.168.1.27:8123` và Long-Lived Token thực tế.
- [x] Đã cấu hình và kết nối thành công Home Assistant WebSocket API trên Pi 5 (`192.168.1.27:8123/api/websocket`).
- [x] SSH vào NAS `nas152@192.168.1.114` khởi chạy container `nala_nas_ws_hub` thành công.
- [x] Hoàn thiện Web Management Hub & WebSocket 2 chiều tại `http://192.168.1.114:8765/admin`:
  - Client WebSocket thời gian thực tự động kết nối, auto-reconnect, hiển thị trạng thái `WS LIVE`.
  - Tự động phát hiện màn hình mới (ví dụ `D6F4`, `881C`) và hiển thị card chờ ghép nối không cần tải lại trang.
  - **Trình Cài Đặt (Installer Wizard)** trực quan 3 bước:
    - 1. Đặt tên phòng, vị trí tầng, trạng thái Master.
    - 2. Thêm, sửa, xóa nút bấm điều khiển Home Assistant tùy ý (chọn từ thực thể thực tế trên Pi 5 như đèn, quạt, máy lạnh, rèm hoặc tự nhập Entity ID; gán icon và nhãn hiển thị tùy biến).
    - 3. Cài đặt phần cứng (độ sáng LCD, âm lượng loa, AI Model) kèm khung xem trước mô phỏng màn hình LCD 240x320 trực tiếp.
  - Đồng bộ cấu hình tức thời xuống màn hình vật lý qua WebSocket frame `config_sync` (<20ms).
  - Phản ánh và điều khiển trạng thái bật/tắt thiết bị HA theo thời gian thực (`ha_state_change` / `ha_action`).

### Phase 2: Nâng Cấp Firmware ESP32-S3 Sang LVGL 8.3.11 Chuẩn & Font Tiếng Việt Có Dấu
- [x] Tích hợp trọn vẹn [ui_lvgl_dashboard.h](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/firmware_esp32s3_panel/include/ui_lvgl_dashboard.h) vào [main.cpp](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/firmware_esp32s3_panel/src/main.cpp).
- [x] Cấu hình Driver LovyanGFX làm Display/Touch Interface cho LVGL với bộ đệm Double Buffer an toàn trong Internal SRAM (`buf1`, `buf2` 240x40) triệt tiêu hoàn toàn nhấp nháy.
- [x] Cảm ứng điện dung FT6336G đảo 180° chuẩn xác không lệch điểm chạm.
- [x] Tích hợp thư viện **`FontMaker`** (Đào Nguyên IOT47) vào [firmware_esp32s3_panel/lib/FontMaker](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/firmware_esp32s3_panel/lib/FontMaker):
  - Khởi tạo `fontMaker(&setpx_font)` qua con trỏ vẽ pixel LovyanGFX `tft.drawPixel(x, y, color)`.
  - Hiển thị Tiếng Việt UTF-8 có dấu đầy đủ (`Tahoma12`, `Tahoma16`) trên màn hình khởi động kết nối WiFi nhà và màn hình cấu hình Soft-AP Captive Portal `192.168.4.1`.
- [x] Xây dựng 3 Tab giao diện cảm ứng:
  - **Tab 1 (Nhà & AI)**: Nút bật/tắt Đèn, Quạt, Rèm (nhận entity từ HA); Khung hiển thị biểu cảm AI và văn bản stream câu trả lời.
  - **Tab 2 (Đàm Thoại Intercom)**: Danh sách nút chọn phòng (*Tầng Trệt, Phòng Khách, Bếp, Lầu 3, Toàn Nhà*) + Nút tròn Push-to-Talk (PTT).
  - **Tab 3 (Cài Đặt)**: Thanh trượt Volume loa, Độ sáng màn hình LCD, Dropdown chọn AI Model (Gemini / DeepSeek), thông tin IP/MAC.
- [x] Ghim `Task_LVGL_UI` vào Core 1 (15ms tick) và `Task_Net_Audio` vào Core 0 (WebSocket + I2S DMA).
- [x] Đồng bộ nút bấm động từ WebSocket: Dashboard tự động cập nhật nhãn nút bấm (`set_button1_config`, `set_button2_config`) và định tuyến thao tác chạm tới đúng `entity_id` người dùng đã cấu hình trên Web.
- [x] Biên dịch thành công (Flash 39.6%, RAM 42.2%) và sẵn sàng nạp xuống bo mạch.

### Phase 3: Hoàn Thiện Luồng Đàm Thoại Nội Bộ PTT & Audio DMA
- [x] Viết FreeRTOS Task thu âm I2S DMA phi chặn trên Core 0 (`audio_es8311_engine.h` & `Task_Net_Audio`).
- [x] Đóng gói mảng âm thanh PCM 16kHz vào cấu trúc Binary 520 byte theo đặc tả [protocol_defs.h](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/firmware_esp32s3_panel/include/protocol_defs.h):
  - `0xA55A` (Magic Word), `sender_id`, `target_id`, `seq_num`, `stream_flag`, 512 bytes PCM, CRC-8.
  - Tự động phát hiện nhả nút PTT để gửi gói `STREAM_FLAG_END` (0x03) kích hoạt Server xử lý STT / AI tức thì.
- [x] **Cơ Chế Định Tuyến Kênh Đàm Thoại Động (Advanced Intercom Router):**
  - Gán và duy trì Intercom ID động (1 byte: `0x01` cho `881C`, `0x02` cho `D6F4`,...) lưu persistent trên NAS Hub.
  - Tự động đồng bộ danh sách kênh đàm thoại (`intercom_targets`) xuống từng màn hình qua `config_sync` và `intercom_sync`.
  - Hỗ trợ đầy đủ Unicast (phòng sang phòng cụ thể), Broadcast toàn bộ các tầng (`0xFF`), và Web Admin Monitor (`0xFE`).
- [x] **Chẩn Đoán Phần Cứng Trực Tiếp Trên Tab 3 Cài Đặt (Hardware Diagnostics):**
  - Thêm 4 nút theo lưới 2x2 tinh gọn:
    - `🔊 Test Loa`: Phát tone sin 1kHz chuẩn trong 1.2s qua ES8311 I2S DMA để kiểm tra loa.
    - `🎙️ Test Mic`: Thu âm 1.5s qua I2S mic, tính cường độ RMS và phát loopback ngay ra loa để nghe lại giọng nói kiểm tra mic.
    - `📡 Test Server`: Bắn gói tin WebSocket `ping` lên NAS Hub, tính độ trễ Round-Trip Time (RTT ms) và báo trạng thái.
    - `⚙️ Đổi WiFi`: Kích hoạt chế độ Soft-AP 192.168.4.1 để cài đặt lại mạng khi đổi phòng.
  - Nhãn chẩn đoán tiếng Việt `lbl_diag_result`: Báo kết quả tức thời trên màn hình ("Loa: Kiểm tra OK!", "Mic: Tốt (RMS: 245, Đã phát lại)!", "Server: Kết nối OK (14 ms)").
- [x] **Khắc Phục Triệt Để Lỗi Đồng Bộ Nút Bấm Home Assistant (State & Action Sync):**
  - `config_sync` trên NAS Hub tự động truy vấn trạng thái thực tế từ `ha_bridge.states` để gán `state`, `is_on`, `domain` cho từng nút bấm của panel.
  - `ha_action` tự động suy diễn domain chính xác (`light`, `switch`, `fan`, `climate`); xử lý riêng biệt máy lạnh `climate` chuyển đổi giữa chế độ `cool` và `off` chuẩn HA.
  - Firmware ESP32 áp dụng phản hồi tức thời (Optimistic UI update) khi chạm nút và tự động cập nhật màu nút theo trạng thái thực tế Home Assistant.
- [x] **Trung Tâm Quản Lý Lịch Sử Giọng Nói & Tự Động Xóa Theo Lịch (History & Auto-Retention):**
  - Module [history_manager.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/app/history_manager.py): Lưu trữ thông tin hội thoại vào `history.json` và file ghi âm WAV chuẩn 16kHz 16-bit Mono vào thư mục `recordings/`.
  - Cơ chế tự động dọn dẹp theo lịch: Người dùng có thể tùy chọn số ngày lưu trữ (`1`, `3`, `7`, `14`, `30 ngày`, hoặc `Không bao giờ xóa`). Task định kỳ tự động quét và xóa sạch file ghi âm cùng bản ghi quá hạn.
  - Giao diện Web Admin Hub ([index.html](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/app/static/index.html)): Thêm Modal `📜 Lịch Sử & Tự Động Xóa` với bảng danh sách thời gian thực, trình phát audio nghe lại trực tiếp trên trình duyệt, bộ lọc AI / Intercom và nút xóa toàn bộ.
- [x] **Biên Dịch & Triển Khai Thực Tế:**
  - Đã triển khai code mới lên NAS Hub `192.168.1.114:8765` và khởi động lại container `nala_nas_ws_hub` thành công.
  - Đã biên dịch firmware `v2.7.0-DIAG-SYNC` thành công (Flash 42.5%, RAM 42.5%).
  - Đã nạp trực tiếp vào bo mạch `D6F4` qua `COM6` thành công.
  - Đã tải file firmware `v2.7.0-DIAG-SYNC` lên NAS Hub sẵn sàng cập nhật OTA cho các màn hình khác trong nhà.
- [x] **Trung Tâm Đàm Thoại Trực Tuyến Trên Web Admin Hub ([index.html](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/app/static/index.html)):**
  - Giao diện bảng điều khiển Intercom: Xem danh sách các phòng online và ID kênh tương ứng.
  - **Web Push-to-Talk (Web PTT)**: Bấm giữ trên trình duyệt máy tính hoặc điện thoại để nói chuyện trực tiếp xuống loa của từng màn hình hoặc gọi toàn nhà qua Web Audio API (16kHz PCM 520 bytes).
  - **Loa Trực Tiếp Trên Trình Duyệt**: Tự động giải mã PCM 16-bit 16kHz và phát ra loa máy tính/điện thoại khi có màn hình nào đang đàm thoại.
  - Nút gọi nhanh "🎙️ Gọi Phòng Này" trên từng thẻ màn hình.
- [x] **Firmware ESP32-S3 Tab 2 (Intercom):**
  - Hiển thị danh sách các phòng thực tế trong nhà (`intercom_targets`) thay vì cố định.
  - Cơ chế Half-Duplex (MUTE loa khi bật Mic) chống hú rít âm thanh giữa Mic và Loa trên cùng bo mạch.
  - Đèn LED RGB WS2812 thông minh: Chuyển màu ĐỎ khi đang đàm thoại phát đi, XANH DƯƠNG khi đang nhận cuộc gọi đến, XANH LÁ khi ở chế độ chờ.
  - Hiển thị dòng trạng thái tiếng Việt trên màn hình: *"Đang nghe đàm thoại..."*, *"Đang phát âm thanh..."*, *"Đàm thoại: Sẵn sàng"*.
- [x] Đã biên dịch thành công bản firmware `v2.6.0-INTERCOM` và đã nạp trực tiếp vào màn hình `881C` cũng như tải lên NAS Hub sẵn sàng OTA.

### Phase 4: Hoàn Thiện Voice AI Pipeline & Tích Hợp Home Assistant
- [x] Kiểm tra kết nối hai chiều [ha_bridge.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/server_nas_hub/app/ha_bridge.py) tới Raspberry Pi 5 (`192.168.1.27:8123`):
  - Lấy danh sách thực thể phòng khách, phòng ngủ thực tế (`light.moes_matter_switch_den_3_6`, `climate.151732606266034_climate`,...).
  - Đã xác thực thành công token HA Long-Lived và duy trì kết nối WebSocket thường trực với Pi 5.
  - Hỗ trợ đầy đủ các domain HA: `light`, `climate`, `fan`, `switch`, `cover`, `scene`, `input_boolean`.
- [x] **Tích Hợp Sâu Home Assistant Area & Floor Registry:**
  - Tự động truy vấn `config/area_registry/list` (9 phòng) và `config/floor_registry/list` (4 tầng: Trệt, Tầng 1, Tầng 2, Tầng 3) trực tiếp từ Home Assistant Pi 5.
  - Sửa lỗi xung đột `id_reuse` / monotonically increasing ID trong WebSocket protocol của Home Assistant.
  - Dropdown chọn phòng trong Trình Cài Đặt (Installer Wizard) tự động điền Tên Phòng và Vị Trí Tầng.
  - Tự động nhóm và ghim các thực thể thuộc đúng phòng lên đầu danh sách (`⭐ Thuộc phòng này`) giúp cấu hình nút bấm tiện lợi.
- [x] **Giao Diện Quản Trị Cấu Hình HA Trực Quan (Web Admin):**
  - Thêm Modal `⚙️ Cấu Hình Kết Nối Home Assistant` với ô nhập WebSocket URL và Access Token bảo mật.
  - Tính năng `🔍 Kiểm Tra Kết Nối (Test Live)` xác thực trực tiếp với Home Assistant và báo số tầng, phòng.
  - Tự động đồng bộ và ghi vào file `.env` trên NAS Hub, kích hoạt kết nối lại tức thời.
- [x] **Xây Dựng Bộ Tích Hợp Home Assistant / HACS ([custom_components/nala_smart_panel](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel)):**
  - Đạt chuẩn HACS với đầy đủ [manifest.json](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/manifest.json), [config_flow.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/config_flow.py), [coordinator.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/coordinator.py), [sensor.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/sensor.py), [button.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/button.py), [number.py](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/homeassistant_integration/custom_components/nala_smart_panel/number.py).
  - Tự động tạo Device cho từng màn hình trên Home Assistant UI, điều khiển độ sáng màn hình, âm lượng loa, đồng bộ và đưa về AP cấu hình.
- [ ] Kiểm tra luồng Voice AI:
  - Mic thu âm ➔ NAS Faster-Whisper nhận dạng tiếng Việt ➔ Router phân tích ý định (Intent) ➔ Gọi HA hoặc Gemini/DeepSeek ➔ Piper TTS sinh giọng nói ➔ Bắn PCM về loa phát mượt mà.

### Phase 5: Nghiệm Thu Thực Địa & Đóng Gói
- [x] Web Admin Hub & WebSocket 2 chiều hoạt động hoàn hảo:
  - Cả 2 màn hình ESP32-S3 (`881C` và `D6F4`) kết nối WebSocket đồng thời, hiển thị trạng thái xanh `ONLINE`.
  - Trình Cài Đặt (Installer Wizard) cho phép tạo, gán icon, chọn entity HA, chỉnh nhãn nút tùy ý cho từng màn hình riêng biệt.
  - Thao tác "LƯU CẤU HÌNH & ĐỒNG BỘ PANEL" đẩy trực tiếp WebSocket `config_sync` tức thời xuống màn hình.
  - Bản vá `WebSocketsSansIOProtocol` trên NAS Hub ngăn chặn 100% lỗi uvicorn crash khi chuỗi tiếng Việt dài.
- [ ] Thử nghiệm thao tác trực tiếp trên màn hình cảm ứng: bật tắt đèn HA, chỉnh volume/độ sáng, gọi PTT sang web simulator / node khác.
- [ ] Xác nhận không có hiện tượng treo luồng, vỡ tiếng, hú mic hay giật khung hình.

---

## 6. Thứ Tự Triển Khai Ngay Bây Giờ (Execution Next Step)
👉 **Bước 1**: Cập nhật cấu hình Docker trên Server NAS Hub (sửa service Piper TTS sang HTTP endpoint chuẩn, cấu hình Whisper GPU cho 1080 Ti), sau đó tự động SSH lên NAS để deploy và chạy thử dịch vụ.  
👉 **Bước 2**: Tái cấu trúc `main.cpp` trên ESP32-S3 để kích hoạt toàn diện giao diện **LVGL 8.3.11** theo đúng Phương án 2 đã chọn.
