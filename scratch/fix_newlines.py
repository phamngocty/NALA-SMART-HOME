import re

# Fix ui_lvgl_dashboard.h
with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'rb') as f:
    u = f.read()

# Replace physical newlines in strings with \n
u = u.replace(b'Serial.printf("[UI-EVENT] CLICKED target=%p\r\n", target);', b'Serial.printf("[UI-EVENT] CLICKED target=%p\\n", target);')
u = u.replace(b'Serial.printf("[UI-EVENT] CLICKED target=%p\n", target);', b'Serial.printf("[UI-EVENT] CLICKED target=%p\\n", target);')
u = u.replace(b'Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p\r\n", target);', b'Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p\\n", target);')
u = u.replace(b'Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p\n", target);', b'Serial.printf("[UI-EVENT] VALUE_CHANGED target=%p\\n", target);')
u = u.replace(b'Serial.printf("[UI-TAB] Chuyen sang Tab %u: %s\r\n", (unsigned int)act_tab, n);', b'Serial.printf("[UI-TAB] Chuyen sang Tab %u: %s\\n", (unsigned int)act_tab, n);')
u = u.replace(b'Serial.printf("[UI-TAB] Chuyen sang Tab %u: %s\n", (unsigned int)act_tab, n);', b'Serial.printf("[UI-TAB] Chuyen sang Tab %u: %s\\n", (unsigned int)act_tab, n);')

with open('firmware_esp32s3_panel/include/ui_lvgl_dashboard.h', 'wb') as f:
    f.write(u)

# Fix main.cpp
with open('firmware_esp32s3_panel/src/main.cpp', 'rb') as f:
    m = f.read()

m = m.replace(b'Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\r\n", ota_val_err, esp_err_to_name(ota_val_err));', b'Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\\n", ota_val_err, esp_err_to_name(ota_val_err));')
m = m.replace(b'Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\n", ota_val_err, esp_err_to_name(ota_val_err));', b'Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\\n", ota_val_err, esp_err_to_name(ota_val_err));')

with open('firmware_esp32s3_panel/src/main.cpp', 'wb') as f:
    f.write(m)

print("Files fixed successfully!")
