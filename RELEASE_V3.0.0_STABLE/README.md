# BẢN PHÁT HÀNH CHUẨN XÁC ĐỊNH: V3.0.0 STABLE (VERIFIED HARDWARE)

- **Ngày giờ biên dịch gốc:** 31/10/2026 18:47:46
- **Tên file gốc trên NAS Hub:** `firmware_20261031_184746_firmware_v3.0.0.bin`
- **Dung lượng:** 1,435,792 bytes (1.37 MB)
- **Mã MD5 Checksum:** `815cd34623db77b051db63daa19021a8`
- **Trạng thái:** ĐÃ KIỂM THỬ THỰC TẾ TRÊN PHẦN CỨNG (Hoạt động hoàn hảo).

---

## 1. Các tính năng nổi bật của bản v3.0.0
1. **Giao diện 4 Tab hoàn chỉnh:**
   - Tab 0: Thiết bị (Lưới 2 cột, scroll mượt mà, hiển thị thiết bị theo phòng cục bộ).
   - Tab 1: Trợ lý AI (Visualizer âm thanh, bong bóng hội thoại AI).
   - Tab 2: Đàm thoại nội bộ (Intercom).
   - Tab 3: Cài đặt (Thanh trượt Mic Gain ES8311, Công tắc chuông, Độ sáng, Âm lượng).
2. **Driver cảm ứng FT6336U mượt mà:**
   - Đọc I2C dạng Single-burst 5-byte (`Wire.requestFrom((uint16_t)0x38, (uint8_t)5)`).
   - Triệt tiêu hoàn toàn xung đột đường I2C với IC âm thanh ES8311, không bị đơ giật.
3. **Độ ổn định cao:**
   - RAM SRAM tiêu thụ ~43%, đảm bảo an toàn tuyệt đối trên bo mạch ES3C28P không có PSRAM ngoài.

---

## 2. Hướng dẫn nạp khi cần khôi phục lại

### Cách 1: Nạp USB (qua COM20) chống lỗi màn hình đen
Chạy lệnh trực tiếp từ thư mục gốc dự án:
```powershell
python flash_tool.py
```
*(Hoặc chạy lệnh esptool trực tiếp)*:
```powershell
python "C:\Users\phamn\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32s3 -p COM20 -b 921600 erase_region 0xe000 0x2000
python "C:\Users\phamn\.platformio\packages\tool-esptoolpy\esptool.py" --chip esp32s3 -p COM20 -b 921600 write_flash 0x10000 RELEASE_V3.0.0_STABLE/firmware_v3.0.0_stable.bin
```

### Cách 2: Cập nhật qua OTA
Bản firmware này đã được đặt làm bản phát hành chính thức (`firmware_latest.bin`) trên NAS Hub.
Chỉ cần truy cập [http://192.168.1.114:8765/admin](http://192.168.1.114:8765/admin) và nhấn nút **Bắt đầu OTA**.
