import re
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

print("Original text length:", len(text))

# 1. Update TARGET_VER
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

# 3. Read tab_role_html
with open('scratch/test_tab_role_html.py', 'r', encoding='utf-8') as f:
    code = f.read()
# extract tab_role_html
start_m = code.find("tab_role_html = '''") + len("tab_role_html = '''")
end_m = code.find("'''", start_m)
tab_role_html = code[start_m:end_m]

# Read ai_modal_inner_body.html
with open('scratch/ai_modal_inner_body.html', 'r', encoding='utf-8') as f:
    ai_inner_body = f.read()

# Replace tab_sys_ha marker to hidden and prepend tab_role_html
old_tab_ha = '<div id="tab_sys_ha" style="display: block;">'
new_tab_ha = '<div id="tab_sys_ha" style="display: none;">'
assert old_tab_ha in text, "Could not find old_tab_ha"
text = text.replace(old_tab_ha, tab_role_html + "\n" + new_tab_ha, 1)

# Replace tab_sys_ai with complete inner body
p_ai_start = text.find('<div id="tab_sys_ai"')
p_ota_start = text.find('<div id="tab_sys_ota"')
assert p_ai_start != -1 and p_ota_start != -1, "Could not find tab_sys_ai or tab_sys_ota"

new_tab_ai = '<div id="tab_sys_ai" style="display: none;">\n' + ai_inner_body + '\n</div>\n'
text = text[:p_ai_start] + new_tab_ai + text[p_ota_start:]

# 4. Update switchSystemSettingsTab
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

text = text.replace("function openSystemSettingsModal(tab = 'ha')", "function openSystemSettingsModal(tab = 'role')")

# 5. Add XiaoZhi Voice Role JS
xiaozhi_js = '''
// --- XIAOZHI VOICE ROLE & VOICE PREVIEW SYSTEM ---
const XZ_VOICES = [
    { id: 'vi-VN-HoaiMyNeural', name: 'Giọng nữ (Female Voice)', sub: 'Hoài My · Tự nhiên, truyền cảm', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-NamMinhNeural', name: 'giọng nam (Male Voice)', sub: 'Nam Minh · Trầm ấm, đĩnh đạc', rate: '+0%', pitch: '+0Hz', vad: 'normal' },
    { id: 'vi-VN-HoaiMyNeural_young', name: 'cô gái trẻ (Young Girl)', sub: 'Trong trẻo, vui tươi, hoạt bát', rate: '+10%', pitch: '+10Hz', vad: 'fast' },
    { id: 'vi-VN-NamMinhNeural_host', name: 'chủ nhà nam (Male Host)', sub: 'Chững chạc, uy quyền, lịch thiệp', rate: '-5%', pitch: '-10Hz', vad: 'slow' },
    { id: 'vi-VN-NamMinhNeural_young', name: 'chàng trai trẻ (Young Man)', sub: 'Nhanh nhẹn, thân thiện, năng động', rate: '+10%', pitch: '+5Hz', vad: 'normal' },
    { id: 'google_fast', name: 'Thử nghiệm · Google Siêu Tốc (0.15s)', sub: 'Phản xạ tức thì, không độ trễ', rate: '+0%', pitch: '+0Hz', vad: 'fast' }
];

let selectedXzVoiceId = 'vi-VN-HoaiMyNeural';
let currentPreviewAudio = null;
let activePreviewBtn = null;

function renderXzVoiceList() {
    const listEl = document.getElementById('xzVoiceList');
    if (!listEl) return;
    const filter = (document.getElementById('xzVoiceSearchInput')?.value || '').toLowerCase().trim();
    
    let html = '';
    XZ_VOICES.forEach(v => {
        if (filter && !v.name.toLowerCase().includes(filter) && !v.sub.toLowerCase().includes(filter)) {
            return;
        }
        const isSelected = (v.id === selectedXzVoiceId);
        const safeBtnId = 'btnPreview_' + v.id.replace(/[^a-zA-Z0-9]/g, '_');
        html += '<div class="xz-voice-item" onclick="selectXiaoZhiVoice(\\'' + v.id + '\\')" style="display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.04); background: ' + (isSelected ? 'rgba(56, 189, 248, 0.08)' : 'transparent') + '; transition: background 0.2s;" onmouseover="this.style.background=\\'rgba(56, 189, 248, 0.12)\\'" onmouseout="this.style.background=\\'' + (isSelected ? 'rgba(56, 189, 248, 0.08)' : 'transparent') + '\\'">'
            + '<div style="display: flex; align-items: center; gap: 10px;">'
            + '<span style="color: #38bdf8; width: 16px; font-weight: bold; font-size: 14px;">' + (isSelected ? '✓' : '') + '</span>'
            + '<div>'
            + '<div style="font-size: 13px; font-weight: 600; color: #f1f5f9;">' + v.name + '</div>'
            + '<div style="font-size: 11px; color: #64748b;">' + v.sub + '</div>'
            + '</div>'
            + '</div>'
            + '<button type="button" id="' + safeBtnId + '" onclick="event.stopPropagation(); playVoicePreviewItem(\\'' + v.id + '\\')" style="background: rgba(56, 189, 248, 0.12); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 12px; transition: all 0.2s;" title="Nghe thử">'
            + '▷'
            + '</button>'
            + '</div>';
    });
    if (!html) {
        html = '<div style="padding: 14px; color: #64748b; font-size: 12px; text-align: center;">Không tìm thấy giọng nói</div>';
    }
    listEl.innerHTML = html;
}

function toggleVoiceDropdown(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('xzVoiceMenu');
    const arrow = document.getElementById('xzDropdownArrow');
    if (!menu) return;
    const isShowing = menu.style.display === 'block';
    menu.style.display = isShowing ? 'none' : 'block';
    if (arrow) arrow.style.transform = isShowing ? 'rotate(0deg)' : 'rotate(180deg)';
    if (!isShowing) {
        renderXzVoiceList();
        const searchInput = document.getElementById('xzVoiceSearchInput');
        if (searchInput) {
            searchInput.value = '';
            setTimeout(() => searchInput.focus(), 50);
        }
    }
}

function filterVoiceList(query) {
    renderXzVoiceList();
}

function selectXiaoZhiVoice(voiceId) {
    selectedXzVoiceId = voiceId;
    const v = XZ_VOICES.find(x => x.id === voiceId);
    if (v) {
        const nameEl = document.getElementById('xzSelectedVoiceName');
        if (nameEl) nameEl.textContent = v.name;
        
        const rateSlider = document.getElementById('xzSpeakingRate');
        if (rateSlider && v.rate) {
            rateSlider.value = v.rate.includes('-') ? 1 : (v.rate === '+0%' ? 2 : 3);
        }
        const pitchSlider = document.getElementById('xzSpeakingPitch');
        if (pitchSlider && v.pitch) {
            pitchSlider.value = v.pitch.includes('-') ? 1 : (v.pitch === '+0Hz' ? 2 : 3);
        }
        const vadSlider = document.getElementById('xzVadSpeed');
        if (vadSlider && v.vad) {
            vadSlider.value = v.vad === 'slow' ? 1 : (v.vad === 'fast' ? 3 : 2);
        }
        updateVoiceSlidersUI();
    }
    const menu = document.getElementById('xzVoiceMenu');
    const arrow = document.getElementById('xzDropdownArrow');
    if (menu) menu.style.display = 'none';
    if (arrow) arrow.style.transform = 'rotate(0deg)';
}

document.addEventListener('click', (e) => {
    const container = document.getElementById('xzVoiceDropdownContainer');
    if (container && !container.contains(e.target)) {
        const menu = document.getElementById('xzVoiceMenu');
        const arrow = document.getElementById('xzDropdownArrow');
        if (menu) menu.style.display = 'none';
        if (arrow) arrow.style.transform = 'rotate(0deg)';
    }
});

function toggleVoiceSettingsPanel() {
    const container = document.getElementById('xzSlidersContainer');
    const arrow = document.getElementById('xzSettingsArrow');
    if (!container) return;
    const isVisible = container.style.display !== 'none';
    container.style.display = isVisible ? 'none' : 'grid';
    if (arrow) arrow.textContent = isVisible ? '▼' : '▲';
}

function updateVoiceSlidersUI() {
    const vadVal = parseInt(document.getElementById('xzVadSpeed')?.value || '2');
    const vadLbl = document.getElementById('xzVadLabel');
    if (vadLbl) {
        vadLbl.textContent = vadVal === 1 ? 'Chậm' : (vadVal === 3 ? 'Nhanh' : 'Chuẩn');
    }

    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const rateLbl = document.getElementById('xzRateLabel');
    if (rateLbl) {
        rateLbl.textContent = rateVal === 1 ? 'Chậm' : (rateVal === 3 ? 'Nhanh' : 'Chuẩn');
    }

    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');
    const pitchLbl = document.getElementById('xzPitchLabel');
    if (pitchLbl) {
        pitchLbl.textContent = pitchVal === 1 ? 'Thấp' : (pitchVal === 3 ? 'Cao' : 'Chuẩn');
    }
}

async function playVoicePreviewItem(voiceId) {
    const safeBtnId = 'btnPreview_' + voiceId.replace(/[^a-zA-Z0-9]/g, '_');
    const btn = document.getElementById(safeBtnId);

    if (currentPreviewAudio) {
        try { currentPreviewAudio.pause(); } catch(e){}
        currentPreviewAudio = null;
    }
    if (activePreviewBtn) {
        activePreviewBtn.innerHTML = '▷';
        activePreviewBtn.style.color = '#38bdf8';
    }

    if (btn) {
        btn.innerHTML = '⏳';
        btn.style.color = '#fbbf24';
        activePreviewBtn = btn;
    }

    let actualVoice = voiceId.split('_')[0];
    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');

    const rateStr = rateVal === 1 ? '-10%' : (rateVal === 3 ? '+10%' : '+0%');
    const pitchStr = pitchVal === 1 ? '-10Hz' : (pitchVal === 3 ? '+10Hz' : '+0Hz');

    const sampleText = "Xin chào! Mình là Nala, trợ lý ảo nhà thông minh của gia đình.";

    try {
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
            if (btn) { btn.innerHTML = '▷'; btn.style.color = '#38bdf8'; }
            alert('Không thể tạo âm thanh nghe thử');
            return;
        }

        const blob = await res.blob();
        const audioUrl = URL.createObjectURL(blob);
        currentPreviewAudio = new Audio(audioUrl);
        currentPreviewAudio.onplay = () => {
            if (btn) { btn.innerHTML = '🔊'; btn.style.color = '#34d399'; }
        };
        currentPreviewAudio.onended = () => {
            if (btn) { btn.innerHTML = '▷'; btn.style.color = '#38bdf8'; }
            activePreviewBtn = null;
        };
        currentPreviewAudio.onerror = () => {
            if (btn) { btn.innerHTML = '▷'; btn.style.color = '#38bdf8'; }
            activePreviewBtn = null;
        };
        await currentPreviewAudio.play();
    } catch (e) {
        console.error("Preview error:", e);
        if (btn) { btn.innerHTML = '▷'; btn.style.color = '#38bdf8'; }
        activePreviewBtn = null;
    }
}

async function loadXiaoZhiVoiceRole() {
    try {
        const res = await fetch('/api/ai/config');
        if (!res.ok) return;
        const data = await res.json();

        selectedXzVoiceId = data.tts_voice || 'vi-VN-HoaiMyNeural';
        const v = XZ_VOICES.find(x => x.id === selectedXzVoiceId);
        const nameEl = document.getElementById('xzSelectedVoiceName');
        if (nameEl) nameEl.textContent = v ? v.name : 'Giọng nữ (Female Voice)';

        const personaEl = document.getElementById('xzRolePersona');
        if (personaEl) {
            personaEl.value = data.voice_persona || "Xin chào! Mình là Nala, trợ lý ảo thông minh của gia đình.\\n\\nMục tiêu chính: Hỗ trợ điều khiển nhà thông minh, theo dõi an ninh và giải đáp thắc mắc tự nhiên.\\n\\nGiọng điệu/Tính cách: Thân thiện, chu đáo, súc tích (1-2 câu ngắn gọn).";
        }

        const rateSlider = document.getElementById('xzSpeakingRate');
        const rate = data.tts_rate || '+0%';
        if (rateSlider) {
            rateSlider.value = rate.includes('-') ? 1 : (rate === '+0%' ? 2 : 3);
        }

        const pitchSlider = document.getElementById('xzSpeakingPitch');
        const pitch = data.tts_pitch || '+0Hz';
        if (pitchSlider) {
            pitchSlider.value = pitch.includes('-') ? 1 : (pitch === '+0Hz' ? 2 : 3);
        }

        const vadSlider = document.getElementById('xzVadSpeed');
        const vad = data.vad_speed || 'normal';
        if (vadSlider) {
            vadSlider.value = vad === 'slow' ? 1 : (vad === 'fast' ? 3 : 2);
        }

        updateVoiceSlidersUI();
        renderXzVoiceList();
    } catch (e) {
        console.error("loadXiaoZhiVoiceRole error:", e);
    }
}

async function saveXiaoZhiVoiceRole() {
    const personaEl = document.getElementById('xzRolePersona');
    const rateVal = parseInt(document.getElementById('xzSpeakingRate')?.value || '2');
    const pitchVal = parseInt(document.getElementById('xzSpeakingPitch')?.value || '2');
    const vadVal = parseInt(document.getElementById('xzVadSpeed')?.value || '2');

    let actualVoice = selectedXzVoiceId.split('_')[0];
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
            alert('✅ Đã lưu thành công Vai trò giọng nói, tốc độ & cao độ XiaoZhi vào NALA Hub!');
        } else {
            alert('❌ Lỗi: ' + (data.message || 'Không thể lưu'));
        }
    } catch (e) {
        alert('Lỗi kết nối: ' + e.message);
    }
}
'''

# 6. Insert JS before </script>
script_end = text.rfind('</script>')
text = text[:script_end] + "\n" + xiaozhi_js + "\n" + text[script_end:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved updated index.html with length:", len(text))
