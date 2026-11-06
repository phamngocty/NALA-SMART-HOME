# Smart Floor & Room Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Triển khai hoàn chỉnh tính năng **Nút Toàn Nhà** & **Cây Phân Tầng Thông Minh (Smart Floor & Room Hub)** trên hệ thống NALA SMART HOME, cho phép màn hình ESP32-S3 đứng tại phòng hiện tại (ví dụ: Phòng ngủ Ty) có thể quan sát trạng thái toàn bộ căn nhà, ưu tiên đẩy phòng có thiết bị bật lên đầu, chuyển nhanh sang điều khiển phòng khác và tự động quay về phòng chính sau thời gian cấu hình trên Web.

**Architecture:** 
- **Server NAS Hub (FastAPI/Python)**: Thu thập toàn bộ thực thể từ Home Assistant, nhóm theo Tầng (`Floor`) và Phòng (`Area`), tạo bản tin `all_rooms_sync` gửi qua WebSocket xuống các Panel.
- **ESP32-S3 Panel (LVGL 8.4 / Arduino)**: Nhận `all_rooms_sync`, quản lý state `home_room` và `current_view_room`. Khi bấm `[Toàn Nhà]`, hiển thị cây phân tầng với thuật toán ưu tiên phòng có thiết bị bật. Khi chọn một phòng khác, chuyển lưới nút điều khiển sang phòng đó, kích hoạt thanh đếm ngược tự về và nút `[🏠 Về Ty]`.
- **Bảo toàn phần cứng**: Giữ nguyên 100% tầng driver âm thanh ES8311, amply FM8002E và cảm ứng FT6336U đã được chứng minh hoạt động hoàn hảo trên `v3.2.1-stable`.

**Tech Stack:** Python 3.11, FastAPI, WebSockets, LovyanGFX, LVGL 8.4, FreeRTOS, ESP32-S3 (Arduino framework, PlatformIO).

**Spec:** [docs/superpowers/specs/2026-11-06-smart-floor-room-hub-design.md](file:///c:/Users/phamn/Documents/PlatformIO/NALA%20SMART%20HOME/docs/superpowers/specs/2026-11-06-smart-floor-room-hub-design.md)

---

### Task 1: Server NAS Hub - Đóng gói dữ liệu `all_rooms_sync` chuẩn
- [ ] File: `server_nas_hub/app/main_ws_server.py`
- [ ] Kiểm tra hàm `build_all_rooms_overview()` hoặc `build_floors_overview()`
- [ ] Đảm bảo mỗi khi thiết bị đăng ký (`register`) hoặc khi có Home Assistant state change, NAS Hub gửi gói tin `all_rooms_sync` chứa:
  - `home_room`: Tên phòng chính của Panel (lấy từ `devices.json`)
  - `room_view_timeout`: Số giây tự về phòng chính (mặc định 15s)
  - `floors`: Danh sách tầng, mỗi tầng gồm danh sách phòng, số lượng thiết bị đang bật và danh sách nút bấm tương ứng
- [ ] **Verify**: Chạy script test Python kết nối WebSocket tới NAS Hub `ws://192.168.1.114:8765/ws/panel` và xác nhận nhận được payload `all_rooms_sync` hợp lệ.

---

### Task 2: Web Dashboard - Cấu hình `room_view_timeout` theo từng Panel
- [ ] File: `server_nas_hub/app/static/index.html`
- [ ] Kiểm tra modal cài đặt panel ("Cài đặt thiết bị"): trường `Thời gian tự quay về phòng chính (giây)` (dropdown: 5s, 10s, 15s, 30s, Không tự về)
- [ ] Đảm bảo khi người dùng lưu cài đặt trên Web, giá trị `room_view_timeout` được ghi vào `devices.json` và phát broadcast lệnh cập nhật xuống màn hình ngay lập tức.
- [ ] **Verify**: Mở Web `http://192.168.1.114:8765`, đổi timeout của phòng ngủ Ty thành 10s, kiểm tra `devices.json` được cập nhật.

---

### Task 3: Firmware ESP32-S3 - Thiết kế UI Cây Phân Tầng & Remote Room View trong `ui_lvgl_dashboard.h`
- [ ] File: `firmware_esp32s3_panel/include/ui_lvgl_dashboard.h`
- [ ] Bổ sung các biến trạng thái:
  - `String home_room_name`
  - `String viewing_room_name`
  - `bool is_viewing_house`
  - `uint16_t room_view_timeout_sec`
  - `uint32_t last_touch_activity_ms`
- [ ] Bổ sung container Header:
  - Nút `[🌐 Toàn Nhà]`
  - Nút `[🏠 Về Phòng Chính]` (chỉ hiển thị khi `viewing_room_name != home_room_name`)
  - Dải đếm ngược `countdown_strip` (hiển thị `⏳ Tự về: XXs`)
- [ ] Cài đặt phương thức:
  - `render_house_floors_view()`: Vẽ danh sách các tầng, tự động sort các phòng có `active_count > 0` lên đầu kèm nhãn màu cam nổi bật.
  - `switch_to_room_view(const char* room_name)`: Chuyển lưới nút bấm điều khiển sang phòng được chọn.
  - `return_to_home_room()`: Quay về phòng chính tức thì.
  - `tick_countdown(uint32_t now_ms)`: Giảm số giây còn lại và tự động gọi `return_to_home_room()` khi hết giờ.
- [ ] **Verify**: Đảm bảo không làm thay đổi các hàm Audio hoặc I2C touch driver.

---

### Task 4: Firmware ESP32-S3 - Tích hợp WebSocket Handlers & Loop Tick trong `main.cpp`
- [ ] File: `firmware_esp32s3_panel/src/main.cpp`
- [ ] Trong `on_ws_text()`: Thêm nhánh xử lý `type == "all_rooms_sync"`:
  - Parse `home_room`, `room_view_timeout`, và mảng `floors`
  - Chuyển tiếp vào `uiDashboard.sync_all_rooms(doc["payload"])`
- [ ] Trong `Task_LVGL_UI` hoặc `loop()`:
  - Gọi `uiDashboard.tick_countdown(millis())` định kỳ 500ms để cập nhật dải đếm ngược.
- [ ] Nâng phiên bản firmware lên **`v3.3.0`**.
- [ ] **Verify**: Biên dịch PlatformIO kiểm tra syntax, RAM và Flash usage.

---

### Task 5: Biên Dịch, Triển Khai OTA v3.3.0 & Nghiệm Thu Thực Tế
- [ ] Biên dịch firmware bằng PlatformIO:
  `& "$env:USERPROFILE\.platformio\penv\Scripts\pio.exe" run -d firmware_esp32s3_panel -e esp32s3_panel`
- [ ] Đẩy firmware `firmware_v3.3.0.bin` lên NAS Hub qua OTA script.
- [ ] Phát lệnh cập nhật OTA cho màn hình Phòng ngủ Ty (`44:1B:F6:CF:88:1C`).
- [ ] Kiểm tra thực tế trên màn hình:
  1. Màn hình khởi động vào Phòng ngủ Ty (5 nút thiết bị).
  2. Bấm nút `[Toàn Nhà]` ➔ Màn hình hiển thị các tầng, các phòng có thiết bị bật nhảy lên đầu.
  3. Bấm vào `Phòng ngủ mẹ` ➔ Màn hình hiện các nút điều khiển phòng mẹ, xuất hiện nút `[🏠 Về Ty]` và thanh đếm ngược 15s.
  4. Thao tác bật/tắt thiết bị phòng mẹ ➔ Home Assistant thực thi thành công, thanh đếm ngược tự reset lại 15s.
  5. Đợi 15s hoặc bấm `[🏠 Về Ty]` ➔ Màn hình tự động quay về Phòng ngủ Ty.
  6. Kiểm tra lại Loa và Mic (Test Mic / Chuông cuộc gọi) vẫn hoạt động hoàn hảo.
