import os
import sys

main_path = os.path.abspath('server_nas_hub/app/main_ws_server.py')
with open(main_path, 'r', encoding='utf-8') as f:
    text = f.read()

# 2. Update registration response to send time_sync and epoch in config_sync
t2 = """                        # Tự động sync cấu hình đã lưu xuống Panel kèm kênh đàm thoại
                        targets = intercom.get_targets(exclude_device_key=code)
                        rname = dev.get("room_name", f"Panel {code}")
                        await websocket.send_json({
                            "type": "config_sync",
                            "payload": {"""

r2 = """                        # Đồng bộ thời gian thực cho RTC nội bộ ESP32Time (1 lần duy nhất khi kết nối)
                        cur_epoch = int(time.time())
                        await websocket.send_json({
                            "type": "time_sync",
                            "epoch": cur_epoch
                        })

                        # Tự động sync cấu hình đã lưu xuống Panel kèm kênh đàm thoại
                        targets = intercom.get_targets(exclude_device_key=code)
                        rname = dev.get("room_name", f"Panel {code}")
                        await websocket.send_json({
                            "type": "config_sync",
                            "epoch": cur_epoch,
                            "payload": {
                                "epoch": cur_epoch,"""

t2_crlf = t2.replace('\n', '\r\n')
r2_crlf = r2.replace('\n', '\r\n')

if t2 in text:
    text = text.replace(t2, r2, 1)
    print("2. Updated registration time sync (LF)")
elif t2_crlf in text:
    text = text.replace(t2_crlf, r2_crlf, 1)
    print("2. Updated registration time sync (CRLF)")
else:
    print("2. t2 not found")

# 3. Handle explicit time_sync_request or get_time
t3 = """                # Đồng bộ cập nhật cài đặt từ Panel lên Server và Web Admin
                elif msg_type == "settings_update":"""

r3 = """                # Yêu cầu lấy giờ từ Panel ESP32
                elif msg_type in ("get_time", "time_sync_request", "time_sync"):
                    await websocket.send_json({
                        "type": "time_sync",
                        "epoch": int(time.time())
                    })

                # Đồng bộ cập nhật cài đặt từ Panel lên Server và Web Admin
                elif msg_type == "settings_update":"""

t3_crlf = t3.replace('\n', '\r\n')
r3_crlf = r3.replace('\n', '\r\n')

if t3 in text:
    text = text.replace(t3, r3, 1)
    print("3. Added time_sync message handler (LF)")
elif t3_crlf in text:
    text = text.replace(t3_crlf, r3_crlf, 1)
    print("3. Added time_sync message handler (CRLF)")
else:
    print("3. t3 not found")

with open(main_path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
print("Saved main_ws_server.py!")
