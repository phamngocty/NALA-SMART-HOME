import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update TARGET_VER to v3.2.0
text = text.replace('var TARGET_VER = "v3.1.0";', 'var TARGET_VER = "v3.2.0";')

# 2. Update wizard-tabs in systemSettingsModal
old_sys_tabs = '''            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_sys_ha_btn" onclick="switchSystemSettingsTab('ha')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    ⚙️ Home Assistant (Pi 5)
                </div>
                <div class="wizard-tab" id="tab_sys_ai_btn" onclick="switchSystemSettingsTab('ai')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🤖 Mô Hình Voice AI &amp; API
                </div>
                <div class="wizard-tab" id="tab_sys_ota_btn" onclick="switchSystemSettingsTab('ota')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🚀 Cập Nhật OTA Firmware
                </div>
            </div>'''

new_sys_tabs = '''            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_sys_role_btn" onclick="switchSystemSettingsTab('role')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎭 Vai Trò &amp; Giọng Nói (XiaoZhi)
                </div>
                <div class="wizard-tab" id="tab_sys_ai_btn" onclick="switchSystemSettingsTab('ai')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🤖 Mô Hình AI &amp; API Key
                </div>
                <div class="wizard-tab" id="tab_sys_ha_btn" onclick="switchSystemSettingsTab('ha')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    ⚙️ Home Assistant (Pi 5)
                </div>
                <div class="wizard-tab" id="tab_sys_ota_btn" onclick="switchSystemSettingsTab('ota')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🚀 Cập Nhật OTA Firmware
                </div>
            </div>'''

assert old_sys_tabs in text, "Could not find old_sys_tabs"
text = text.replace(old_sys_tabs, new_sys_tabs, 1)

# 3. Add tab_sys_role content before tab_sys_ha
old_tab_ha_marker = '<div id="tab_sys_ha" style="display: block;">'
new_tab_ha_marker = '<div id="tab_sys_ha" style="display: none;">'
text = text.replace(old_tab_ha_marker, new_tab_ha_marker, 1)

tab_role_html = '''<div id="tab_sys_role" style="display: block; padding: 24px;">
                    <div style="background: #182234; border: 1px solid #334155; border-radius: 14px; padding: 20px; margin-bottom: 20px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                            <h4 style="margin: 0; font-size: 15px; color: #f8fafc; font-weight: 700; display: flex; align-items: center; gap: 8px;">
                                <span>Vai trò giọng nói (Voice Role Persona)</span>
                            </h4>
                            <span style="font-size: 11px; background: rgba(56, 189, 248, 0.15); color: #38bdf8; padding: 3px 10px; border-radius: 6px; font-weight: 700;">XiaoZhi Standard</span>
                        </div>

                        <!-- Language & Voice Selection Row -->
                        <div style="display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap;">
                            <div style="min-width: 130px; background: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 10px 14px; display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: #fff;">
                                <span>🌐 Tiếng Việt</span>
                            </div>
                            <div style="flex: 1; min-width: 280px; position: relative;">
                                <select id="xzVoiceSelect" onchange="onXzVoiceChange(this.value)" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;">
                                    <option value="vi-VN-HoaiMyNeural" data-rate="+0%" data-pitch="+0Hz">👩 Giọng nữ (Female Voice) - Hoài My [Tự nhiên, truyền cảm]</option>
                                    <option value="vi-VN-NamMinhNeural" data-rate="+0%" data-pitch="+0Hz">👨 Giọng nam (Male Voice) - Nam Minh [Trầm ấm, đĩnh đạc]</option>
                                    <option value="vi-VN-HoaiMyNeural_young" data-rate="+10%" data-pitch="+10Hz">👧 Cô gái trẻ (Young Girl) [Trong trẻo, hoạt bát]</option>
                                    <option value="vi-VN-NamMinhNeural_host" data-rate="-5%" data-pitch="-10Hz">🤵 Chủ nhà nam (Male Host) [Chững chạc, uy quyền]</option>
                                    <option value="vi-VN-NamMinhNeural_young" data-rate="+10%" data-pitch="+5Hz">🧑 Chàng trai trẻ (Young Man) [Nhanh nhẹn, năng động]</option>
                                    <option value="google_fast" data-rate="+0%" data-pitch="+0Hz">⚡ Thử nghiệm · Google Siêu Tốc (0.15s)</option>
                                </select>
                            </div>
                            <button type="button" id="btnPreviewVoice" onclick="playVoicePreview()" style="background: linear-gradient(135deg, #0284c7, #06b6d4); color: white; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.35);">
                                ▶️ Nghe Thử Giọng
                            </button>
                        </div>

                        <!-- Giới thiệu vai trò (Role Persona) -->
                        <div style="margin-bottom: 20px;">
                            <label style="display: block; font-size: 13px; font-weight: 700; color: #38bdf8; margin-bottom: 8px;">
                                Giới thiệu vai trò (Prompt Persona):
                            </label>
                            <textarea id="xzRolePersona" rows="4" style="width: 100%; box-sizing: border-box; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 12px 14px; border-radius: 8px; font-size: 13px; line-height: 1.5; font-family: inherit; resize: vertical;" placeholder="Xin chào! Mình là Nala, trợ lý giọng nói của gia đình bạn..."></textarea>
                            <span style="font-size: 11px; color: #94a3b8; display: block; margin-top: 4px;">
                                Định hình tính cách, phong cách xưng hô và thái độ phản hồi của Nala trên các bảng điều khiển.
                            </span>
                        </div>

                        <!-- Cài đặt giọng nói (Voice Sliders) -->
                        <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px;">
                            <div style="font-size: 14px; font-weight: 700; color: #f8fafc; margin-bottom: 16px;">
                                Cài đặt giọng nói
                            </div>

                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                                <!-- Slider 1: Tốc độ nhận dạng -->
                                <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 14px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                                        <span>Tốc độ nhận dạng</span>
                                        <span id="xzVadLabel" style="color: #38bdf8;">Chuẩn</span>
                                    </div>
                                    <input type="range" id="xzVadSpeed" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 4px;">
                                        <span>Chậm</span>
                                        <span>Chuẩn</span>
                                        <span>Nhanh</span>
                                    </div>
                                </div>

                                <!-- Slider 2: Tốc độ trả lời -->
                                <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 14px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                                        <span>Tốc độ trả lời</span>
                                        <span id="xzRateLabel" style="color: #38bdf8;">Chuẩn (0%)</span>
                                    </div>
                                    <input type="range" id="xzSpeakingRate" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 4px;">
                                        <span>Chậm</span>
                                        <span>Chuẩn</span>
                                        <span>Nhanh</span>
                                    </div>
                                </div>

                                <!-- Slider 3: Cao độ trả lời -->
                                <div style="background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 14px;">
                                    <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 700; color: #cbd5e1; margin-bottom: 8px;">
                                        <span>Cao độ trả lời</span>
                                        <span id="xzPitchLabel" style="color: #38bdf8;">Chuẩn (0Hz)</span>
                                    </div>
                                    <input type="range" id="xzSpeakingPitch" min="1" max="3" step="1" value="2" oninput="updateVoiceSlidersUI()" style="width: 100%; cursor: pointer; accent-color: #38bdf8;">
                                    <div style="display: flex; justify-content: space-between; font-size: 11px; color: #64748b; margin-top: 4px;">
                                        <span>Thấp</span>
                                        <span>Chuẩn</span>
                                        <span>Cao</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Action Button Bar -->
                        <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px;">
                            <button type="button" onclick="saveXiaoZhiVoiceRole()" style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 10px 24px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);">
                                💾 Lưu Vai Trò &amp; Cài Đặt Giọng Nói
                            </button>
                        </div>
                    </div>
                </div>\n'''

text = text.replace(new_tab_ha_marker, tab_role_html + new_tab_ha_marker, 1)

# 4. Update switchSystemSettingsTab JS function
old_switch_sys = '''function switchSystemSettingsTab(tabId) {
    const tabs = ['ha', 'ai', 'ota'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_sys_${t}_btn`);
        const content = document.getElementById(`tab_sys_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'ha') loadHAConfig();
    if (tabId === 'ai') loadAIConfig();
    if (tabId === 'ota') loadOTAFiles();
}'''

new_switch_sys = '''function switchSystemSettingsTab(tabId) {
    const tabs = ['role', 'ai', 'ha', 'ota'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_sys_${t}_btn`);
        const content = document.getElementById(`tab_sys_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'role') loadXiaoZhiVoiceRole();
    if (tabId === 'ha') loadHAConfig();
    if (tabId === 'ai') loadAIConfig();
    if (tabId === 'ota') loadOTAFiles();
}'''

assert old_switch_sys in text, "Could not find old_switch_sys"
text = text.replace(old_switch_sys, new_switch_sys, 1)

# Also update openSystemSettingsModal default tab to 'role'
text = text.replace("function openSystemSettingsModal(tab = 'ha')", "function openSystemSettingsModal(tab = 'role')")

# 5. Add XiaoZhi Voice Role JS functions
js_xiaozhi_role = '''
// --- XIAOZHI VOICE ROLE & SPEECH SLIDERS IMPLEMENTATION ---
let currentPreviewAudio = null;

async function loadXiaoZhiVoiceRole() {
    try {
        const res = await fetch('/api/ai/config');
        if (!res.ok) return;
        const data = await res.json();

        // 1. Voice select
        const vSelect = document.getElementById('xzVoiceSelect');
        const savedVoice = data.tts_voice || 'vi-VN-HoaiMyNeural';
        if (vSelect) {
            let found = false;
            for (let i = 0; i < vSelect.options.length; i++) {
                if (vSelect.options[i].value === savedVoice) {
                    vSelect.selectedIndex = i;
                    found = true;
                    break;
                }
            }
            if (!found) vSelect.value = 'vi-VN-HoaiMyNeural';
        }

        // 2. Role persona
        const personaEl = document.getElementById('xzRolePersona');
        if (personaEl) {
            personaEl.value = data.voice_persona || "Xin chào! Mình là Nala, trợ lý giọng nói của gia đình bạn.\\n\\nMục tiêu chính: Hỗ trợ điều khiển thiết bị, theo dõi an ninh và giải đáp câu hỏi tự nhiên.\\n\\nGiọng điệu/Tính cách: Thân thiện, chu đáo, súc tích (1-2 câu ngắn gọn).";
        }

        // 3. Rate slider (-10%, 0%, +10%)
        const rateSlider = document.getElementById('xzSpeakingRate');
        const rate = data.tts_rate || '+0%';
        if (rateSlider) {
            if (rate.includes('-')) rateSlider.value = 1;
            else if (rate === '+0%' || rate === '0%') rateSlider.value = 2;
            else rateSlider.value = 3;
        }

        // 4. Pitch slider (-10Hz, 0Hz, +10Hz)
        const pitchSlider = document.getElementById('xzSpeakingPitch');
        const pitch = data.tts_pitch || '+0Hz';
        if (pitchSlider) {
            if (pitch.includes('-')) pitchSlider.value = 1;
            else if (pitch === '+0Hz' || pitch === '0Hz') pitchSlider.value = 2;
            else pitchSlider.value = 3;
        }

        // 5. VAD speed
        const vadSlider = document.getElementById('xzVadSpeed');
        const vad = data.vad_speed || 'normal';
        if (vadSlider) {
            if (vad === 'slow') vadSlider.value = 1;
            else if (vad === 'fast') vadSlider.value = 3;
            else vadSlider.value = 2;
        }

        updateVoiceSlidersUI();
    } catch (e) {
        console.error("loadXiaoZhiVoiceRole error:", e);
    }
}

function updateVoiceSlidersUI() {
    // VAD
    const vadVal = parseInt(document.getElementById('xzVadSpeed')?.value || '2');
    const vadLbl = document.getElementById('xzVadLabel');
    if (vadLbl) {
        vadLbl.textContent = vadVal === 1 ? 'Chậm (800ms)' : (vadVal === 3 ? 'Nhanh (300ms)' : 'Chuẩn (500ms)');
    }

    // Rate
    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const rateLbl = document.getElementById('xzRateLabel');
    if (rateLbl) {
        rateLbl.textContent = rateVal === 1 ? 'Chậm (-10%)' : (rateVal === 3 ? 'Nhanh (+10%)' : 'Chuẩn (0%)');
    }

    // Pitch
    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');
    const pitchLbl = document.getElementById('xzPitchLabel');
    if (pitchLbl) {
        pitchLbl.textContent = pitchVal === 1 ? 'Thấp (-10Hz)' : (pitchVal === 3 ? 'Cao (+10Hz)' : 'Chuẩn (0Hz)');
    }
}

function onXzVoiceChange(val) {
    const vSelect = document.getElementById('xzVoiceSelect');
    if (!vSelect) return;
    const opt = vSelect.options[vSelect.selectedIndex];
    const rateAttr = opt.getAttribute('data-rate');
    const pitchAttr = opt.getAttribute('data-pitch');

    const rateSlider = document.getElementById('xzSpeakingRate');
    if (rateSlider && rateAttr) {
        if (rateAttr.includes('-')) rateSlider.value = 1;
        else if (rateAttr === '+0%') rateSlider.value = 2;
        else rateSlider.value = 3;
    }

    const pitchSlider = document.getElementById('xzSpeakingPitch');
    if (pitchSlider && pitchAttr) {
        if (pitchAttr.includes('-')) pitchSlider.value = 1;
        else if (pitchAttr === '+0Hz') pitchSlider.value = 2;
        else pitchSlider.value = 3;
    }
    updateVoiceSlidersUI();
}

async function playVoicePreview() {
    const btn = document.getElementById('btnPreviewVoice');
    const vSelect = document.getElementById('xzVoiceSelect');
    if (!vSelect) return;

    let rawVal = vSelect.value;
    let actualVoice = rawVal.split('_')[0]; // Clean preset tags like vi-VN-NamMinhNeural_host

    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');

    const rateStr = rateVal === 1 ? '-10%' : (rateVal === 3 ? '+10%' : '+0%');
    const pitchStr = pitchVal === 1 ? '-10Hz' : (pitchVal === 3 ? '+10Hz' : '+0Hz');

    const sampleText = "Xin chào! Mình là Nala, trợ lý giọng nói và quản gia nhà thông minh của bạn.";

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '⏳ Đang phát...';
    }

    try {
        if (currentPreviewAudio) {
            try { currentPreviewAudio.pause(); } catch(e){}
        }

        const res = await fetch('/api/tts/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: sampleText,
                voice: actualVoice,
                rate: rateStr,
                pitch: pitchStr
            })
        });

        if (!res.ok) {
            alert('Không thể tạo âm thanh nghe thử');
            return;
        }

        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        currentPreviewAudio = new Audio(audioUrl);
        currentPreviewAudio.onended = () => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '▶️ Nghe Thử Giọng';
            }
        };
        currentPreviewAudio.onerror = () => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '▶️ Nghe Thử Giọng';
            }
        };
        await currentPreviewAudio.play();
    } catch (err) {
        alert('Lỗi nghe thử: ' + err.message);
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '▶️ Nghe Thử Giọng';
        }
    }
}

async function saveXiaoZhiVoiceRole() {
    const vSelect = document.getElementById('xzVoiceSelect');
    const personaEl = document.getElementById('xzRolePersona');
    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');
    const vadVal = parseInt(document.getElementById('xzVadSpeed')?.value || '2');

    let rawVal = vSelect ? vSelect.value : 'vi-VN-HoaiMyNeural';
    let actualVoice = rawVal.split('_')[0];

    const rateStr = rateVal === 1 ? '-10%' : (rateVal === 3 ? '+10%' : '+0%');
    const pitchStr = pitchVal === 1 ? '-10Hz' : (pitchVal === 3 ? '+10Hz' : '+0Hz');
    const vadStr = vadVal === 1 ? 'slow' : (vadVal === 3 ? 'fast' : 'normal');
    const persona = personaEl ? personaEl.value.trim() : '';

    try {
        const curRes = await fetch('/api/ai/config');
        const curConfig = curRes.ok ? await curRes.json() : {};

        const payload = Object.assign({}, curConfig, {
            tts_voice: actualVoice,
            tts_rate: rateStr,
            tts_pitch: pitchStr,
            vad_speed: vadStr,
            voice_persona: persona
        });

        const res = await fetch('/api/ai/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert('✅ Tuyệt vời! Đã lưu thành công Vai trò giọng nói, tốc độ & cao độ XiaoZhi vào NALA Hub.');
        } else {
            alert('❌ Lỗi: ' + (data.message || 'Không thể lưu'));
        }
    } catch (e) {
        alert('Lỗi kết nối: ' + e.message);
    }
}
'''

# Insert js_xiaozhi_role before </script></body>
script_end = text.rfind('</script>')
text = text[:script_end] + "\n" + js_xiaozhi_role + "\n" + text[script_end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("✅ Applied XiaoZhi Voice Role & Speech Sliders to index.html v3.2.0 successfully!")
