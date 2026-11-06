import os

main_path = os.path.abspath('firmware_esp32s3_panel/src/main.cpp')
with open(main_path, 'r', encoding='utf-8') as f:
    text = f.read()

is_crlf = '\r\n' in text
nl = '\r\n' if is_crlf else '\n'

target = f'''    }} else if (type == "ack_chime") {{
        Serial.println("[AI] Nhan lenh phat am thanh nhan lenh Poong!");
        audioEngine.play_ack_chime();
        if (taken) uiDashboard.set_ai_state("thinking", "Đang xử lý...");
    }} else if (type == "ai_state") {{'''

repl = f'''    }} else if (type == "ack_chime") {{
        Serial.println("[AI] Nhan lenh phat am thanh nhan lenh Poong!");
        audioEngine.play_ack_chime();
        if (taken) uiDashboard.set_ai_state("thinking", "Đang xử lý...");
    }} else if (type == "done_chime") {{
        Serial.println("[AI] Nhan lenh phat am thanh hoan thanh Ting!");
        audioEngine.play_done_chime();
    }} else if (type == "ai_state") {{'''

target_norm = target.replace('\n', nl)
repl_norm = repl.replace('\n', nl)

if target_norm in text:
    text = text.replace(target_norm, repl_norm, 1)
    print("Added done_chime to main.cpp")
elif target in text:
    text = text.replace(target, repl, 1)
    print("Added done_chime to main.cpp (LF)")
else:
    print("Target not found in main.cpp")

with open(main_path, 'w', encoding='utf-8', newline='') as f:
    f.write(text)
