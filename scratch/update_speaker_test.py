with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    c = f.read()

import re

pattern = r'void run_speaker_test\(\)\s*\{[\s\S]*?Serial\.println\("\[DIAG\] Test Loa thành công!"\);\s*\}'

replacement = '''void run_speaker_test() {
    Serial.println("[DIAG] Bắt đầu test Loa đa cực PA_EN (ES3C28P Hardware)...");
    uiDashboard.set_diag_result("Loa: Đang phát thử âm thanh...", 0x38BDF8);
    rgb_led.setPixelColor(0, rgb_led.Color(0, 100, 255));
    rgb_led.show();

    audioEngine.set_speaker_volume(100);

    // Giai đoạn 1: Test PA_EN = LOW (Chuẩn Amply SC8002B)
    Serial.println("[DIAG] Giai đoạn 1: PA_EN = LOW (Tone 1000Hz)...");
    pinMode(PA_EN_PIN, OUTPUT);
    digitalWrite(PA_EN_PIN, LOW);
    audioEngine.play_tone(1000, 600, 1.0f);
    delay(100);

    // Giai đoạn 2: Test PA_EN = HIGH (Phòng trường hợp mạch có BJT nghịch)
    Serial.println("[DIAG] Giai đoạn 2: PA_EN = HIGH (Tone 1500Hz)...");
    digitalWrite(PA_EN_PIN, HIGH);
    audioEngine.play_tone(1500, 600, 1.0f);
    delay(100);

    // Giai đoạn 3: Phát chuông Ding-Dong
    Serial.println("[DIAG] Giai đoạn 3: Phát chuông Ding-Dong...");
    audioEngine.play_ringtone();

    // Mute sau khi test xong
    audioEngine.mute_speaker(true);

    rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));
    rgb_led.show();
    uiDashboard.set_diag_result("Loa: Kiểm tra hoàn tất!", 0x10B981);
    Serial.println("[DIAG] Hoàn tất test loa!");
}'''

new_c, count = re.subn(pattern, replacement, c)
if count > 0:
    with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
        f.write(new_c)
    print("Updated run_speaker_test successfully! Count:", count)
else:
    print("Pattern not matched!")
