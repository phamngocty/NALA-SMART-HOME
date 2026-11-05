with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    c = f.read()

import re

# Update version to v3.2.0
c = c.replace('#define CURRENT_FIRMWARE_VERSION "v3.1.5"', '#define CURRENT_FIRMWARE_VERSION "v3.2.0"')
c = c.replace('#define CURRENT_FIRMWARE_VERSION "v3.0.0"', '#define CURRENT_FIRMWARE_VERSION "v3.2.0"')

# Refine run_speaker_test()
speaker_pattern = r'void run_speaker_test\(\)\s*\{[\s\S]*?Serial\.println\("\[DIAG\] Hoàn tất test loa!"\);\s*\}'
speaker_replacement = '''void run_speaker_test() {
    Serial.println("[DIAG] Bắt đầu test Loa (ES3C28P Hardware)...");
    uiDashboard.set_diag_result("Loa: Đang phát thử âm thanh...", 0x38BDF8);
    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255));
    rgb_led.show();

    audioEngine.mute_speaker(false);
    audioEngine.set_speaker_volume(95);

    // 1. Tone 1000Hz (0.5s)
    audioEngine.play_tone(1000, 500, 0.95f);
    delay(80);

    // 2. Chuông đàm thoại Ding-Dong du dương
    audioEngine.play_ringtone();

    // Mute loa sau khi test xong
    audioEngine.mute_speaker(true);

    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
    rgb_led.show();
    uiDashboard.set_diag_result("Loa: Kiểm tra hoàn tất!", 0x10B981);
    Serial.println("[DIAG] Hoàn tất test loa!");
}'''

new_c, count = re.subn(speaker_pattern, speaker_replacement, c)
if count > 0:
    c = new_c
    print("Replaced run_speaker_test!")

with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
    f.write(c)

print("main.cpp updated with version v3.2.0!")
