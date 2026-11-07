path = 'firmware_esp32s3_panel/src/main.cpp'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''    } else if (type == "sentence_start") {
        String sent_txt = doc["payload"]["text"] | "";
        int sent_idx = doc["payload"]["index"] | 0;
        Serial.printf("[AI] Sentence %d bat dau phat: %s\\n", sent_idx, sent_txt.c_str());
        if (taken) {
            uiDashboard.set_ai_state("speaking", sent_txt.c_str());
            xSemaphoreGive(lvgl_mutex);
        }
        return;'''

new_block = '''    } else if (type == "tts") {
        String st = doc["state"] | "";
        if (st == "sentence_start") {
            String sent_txt = doc["text"] | "";
            int sent_idx = doc["index"] | 0;
            Serial.printf("[AI TTS] sentence_start #%d: %s\\n", sent_idx, sent_txt.c_str());
            if (taken) {
                uiDashboard.set_ai_sentence(sent_txt.c_str());
                xSemaphoreGive(lvgl_mutex);
            }
            return;
        } else if (st == "stop") {
            audioEngine.stop_playback();
            if (taken) {
                uiDashboard.set_ai_state("idle", "");
                xSemaphoreGive(lvgl_mutex);
            }
            return;
        }
    } else if (type == "sentence_start") {
        String sent_txt = doc["payload"]["text"] | doc["text"] | "";
        int sent_idx = doc["payload"]["index"] | doc["index"] | 0;
        Serial.printf("[AI] sentence_start #%d: %s\\n", sent_idx, sent_txt.c_str());
        if (taken) {
            uiDashboard.set_ai_sentence(sent_txt.c_str());
            xSemaphoreGive(lvgl_mutex);
        }
        return;'''

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched main.cpp sentence_start handling successfully!")
else:
    print("Could not find old_block in main.cpp")
