# NALA SMART HOME PANEL - BỘ TÍCH HỢP HOME ASSISTANT (HACS & CUSTOM COMPONENT)

Bộ tích hợp chính thức cho hệ sinh thái **NALA Smart Home**, cho phép Home Assistant tự động nhận diện, giám sát và điều khiển toàn bộ các Màn Hình Gắn Tường (ESP32-S3 Wall Panels) thông qua **NALA Central Hub (NAS/Docker)**.

---

## 🌟 CÁC TÍNH NĂNG CHÍNH

1. **Tự động nhận diện thiết bị (Auto Device Discovery):**
   - Mỗi màn hình gắn tường (`881C`, `D6F4`,...) sau khi ghép nối sẽ tự động xuất hiện thành một **Device** riêng biệt trong Home Assistant.
   - Tự động gán vào đúng **Phòng (Area)** và **Tầng (Floor)** theo cấu hình.
2. **Giám sát trạng thái thời gian thực:**
   - Trạng thái kết nối: `Online` / `Offline`.
   - Địa chỉ IP nội mạng của từng màn hình.
   - Danh sách các nút bấm đang hoạt động trên màn hình.
3. **Điều khiển phần cứng từ Home Assistant:**
   - **Độ sáng màn hình (Brightness slider):** Điều chỉnh từ xa 10% - 100%.
   - **Âm lượng loa (Volume slider):** Điều chỉnh từ xa 0% - 100%.
4. **Nút tác vụ nhanh (Quick Action Buttons):**
   - 🔄 **Đồng bộ màn hình (Sync):** Đẩy tức thời bố cục nút bấm và trạng thái xuống màn hình qua WebSocket.
   - ⚙️ **Chuyển về AP cấu hình (192.168.4.1):** Đưa màn hình về chế độ phát Soft-AP để đổi WiFi mà không cần thao tác vật lý.
   - 🔁 **Khởi động lại (Reboot):** Khởi động lại màn hình từ xa khi cần.

---

## 🚀 HƯỚNG DẪN CÀI ĐẶT

### Cách 1: Cài đặt thủ công qua File Editor / Samba (Khuyên dùng)

1. Sao chép toàn bộ thư mục `custom_components/nala_smart_panel` vào thư mục `custom_components` trên Home Assistant của bạn:
   ```
   /config/custom_components/nala_smart_panel/
   ├── __init__.py
   ├── const.py
   ├── coordinator.py
   ├── config_flow.py
   ├── sensor.py
   ├── button.py
   ├── number.py
   ├── manifest.json
   └── hacs.json
   ```
2. Khởi động lại Home Assistant (**Settings -> System -> Restart**).
3. Sau khi khởi động xong:
   - Vào **Settings** (Cài đặt) -> **Devices & Services** (Thiết bị & Dịch vụ).
   - Bấm **Add Integration** (Thêm tích hợp).
   - Tìm kiếm từ khóa: `NALA Smart Panel Central Hub`.
   - Điền IP NAS Hub: `192.168.1.114` (Port: `8765`).
   - Bấm **Submit** -> Home Assistant sẽ kết nối và tự động nạp tất cả các màn hình NALA!

### Cách 2: Cài đặt qua HACS (Custom Repository)

1. Mở **HACS** trên Home Assistant.
2. Bấm vào dấu 3 chấm góc phải trên -> chọn **Custom repositories**.
3. Dán đường dẫn repository của bạn và chọn category là **Integration**.
4. Bấm **Download** và khởi động lại Home Assistant.

---

## 🛠️ THÔNG TIN KẾT NỐI MẶC ĐỊNH

- **NAS Central Hub:** `http://192.168.1.114:8765`
- **Giao diện Web Quản trị:** `http://192.168.1.114:8765/admin`
- **Home Assistant Pi 5:** `http://192.168.1.27:8123`
