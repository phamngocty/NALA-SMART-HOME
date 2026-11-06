import os

path = os.path.abspath('firmware_esp32s3_panel/include/audio_es8311_engine.h')
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

is_crlf = '\r\n' in text
nl = '\r\n' if is_crlf else '\n'

target = f'''    // Phat am thanh da nhan tron ven cau lenh ("Poong!" - Xiaozhi Ack Style)
    void play_ack_chime() {{
        write_reg(0x31, 0x00);
        write_reg(0x32, 0xBF); // 0dB
        mute_speaker(false);
        delay(15);
        play_tone(880, 50, 0.75f);  // A5
        delay(15);
        play_tone(659, 80, 0.70f);  // E5
        delay(20);
        mute_speaker(true);
    }}'''

repl = f'''    // Phat am thanh da nhan tron ven cau lenh ("Poong!" - Xiaozhi Ack Style)
    void play_ack_chime() {{
        write_reg(0x31, 0x00);
        write_reg(0x32, 0xBF); // 0dB
        mute_speaker(false);
        delay(15);
        play_tone(880, 50, 0.75f);  // A5
        delay(15);
        play_tone(659, 80, 0.70f);  // E5
        delay(20);
        mute_speaker(true);
    }}

    // Phat am thanh thuc hien thanh cong ("Ting!" - Google Home / Xiaozhi Done Style)
    void play_done_chime() {{
        write_reg(0x31, 0x00);
        write_reg(0x32, 0xC4); // +3dB
        mute_speaker(false);
        delay(15);
        play_tone(1318, 80, 0.85f); // E6 (1318Hz, 80ms)
        delay(20);
        mute_speaker(true);
    }}'''

target_norm = target.replace('\n', nl)
repl_norm = repl.replace('\n', nl)

if target_norm in text:
    text = text.replace(target_norm, repl_norm, 1)
    print("Added play_done_chime to audio_es8311_engine.h")
elif target in text:
    text = text.replace(target, repl, 1)
    print("Added play_done_chime to audio_es8311_engine.h (LF)")
else:
    print("Target not found")

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
