import re

path = 'firmware_esp32s3_panel/src/main.cpp'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Bump version and include esp_ota_ops.h
pattern1 = r'#include "ota_manager\.h"\s+volatile bool is_ota_running = false;\s+#define CURRENT_FIRMWARE_VERSION "[^"]+"'
replace1 = '''#include "ota_manager.h"
#include "esp_ota_ops.h"
volatile bool is_ota_running = false;
#define CURRENT_FIRMWARE_VERSION "v3.1.5"'''

text, cnt1 = re.subn(pattern1, replace1, text)
print(f"Patch 1 (Version & OTA header): {cnt1}")
assert cnt1 == 1, "Failed to match version header!"

# 2. Add esp_ota_mark_app_valid_cancel_rollback in setup()
pattern2 = r'(Serial\.begin\(115200\);.*?\n)'
replace2 = r'''\1    // Validate running partition to prevent rollback
    esp_err_t ota_val_err = esp_ota_mark_app_valid_cancel_rollback();
    Serial.printf("[SYSTEM] OTA Partition Validate: %d (%s)\n", ota_val_err, esp_err_to_name(ota_val_err));
'''

text, cnt2 = re.subn(pattern2, replace2, text, count=1)
print(f"Patch 2 (OTA validate): {cnt2}")
assert cnt2 == 1, "Failed to add OTA validate!"

# 3. Increase scroll_limit to 35
text = text.replace('indev_drv.scroll_limit = 25;', 'indev_drv.scroll_limit = 35;')

with open(path, 'w', encoding='utf-8', newline='\r\n') as f:
    f.write(text)

print("main.cpp patched successfully!")
