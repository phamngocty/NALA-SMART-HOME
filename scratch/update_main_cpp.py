path = "firmware_esp32s3_panel/src/main.cpp"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = '    if (type == "ai_state") {'
replacement = """    if (type == "wake_chime") {
        Serial.println("[AI] Nhan lenh phat am thanh thuc tinh Ding!");
        audioEngine.play_wake_chime();
        if (taken) uiDashboard.set_ai_state("listening", "Đang nghe...");
    } else if (type == "ack_chime") {
        Serial.println("[AI] Nhan lenh phat am thanh nhan lenh Poong!");
        audioEngine.play_ack_chime();
        if (taken) uiDashboard.set_ai_state("thinking", "Đang xử lý...");
    } else if (type == "ai_state") {"""

if 'if (type == "wake_chime")' not in content:
    idx = content.find(target)
    if idx != -1:
        new_content = content[:idx] + replacement + content[idx + len(target):]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Successfully updated main.cpp with wake_chime and ack_chime!")
    else:
        print("Target not found")
else:
    print("Already updated")
