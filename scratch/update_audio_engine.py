path = "firmware_esp32s3_panel/include/audio_es8311_engine.h"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = "    void play_ringtone() {"
addition = """    // Phat am thanh thuc tinh Wake Word ("Ding!" - Xiaozhi / Gemini Live Style)
    void play_wake_chime() {
        write_reg(0x31, 0x00); // Unmute DAC
        write_reg(0x32, 0xC4); // +3dB
        mute_speaker(false);   // Mo PA
        delay(20);
        play_tone(1046, 70, 0.85f); // C6
        delay(15);
        play_tone(1318, 110, 0.90f); // E6
        delay(25);
        mute_speaker(true);
    }

    // Phat am thanh da nhan tron ven cau lenh ("Poong!" - Xiaozhi Ack Style)
    void play_ack_chime() {
        write_reg(0x31, 0x00);
        write_reg(0x32, 0xBF); // 0dB
        mute_speaker(false);
        delay(15);
        play_tone(880, 50, 0.75f);  // A5
        delay(15);
        play_tone(659, 80, 0.70f);  // E5
        delay(20);
        mute_speaker(true);
    }

"""

if "play_wake_chime" not in content:
    idx = content.find("    void play_ringtone() {")
    if idx != -1:
        new_content = content[:idx] + addition + content[idx:]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully added play_wake_chime and play_ack_chime!")
    else:
        print("Target not found")
else:
    print("Already exists")
