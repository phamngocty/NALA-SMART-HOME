import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Read source file
with open('server_nas_hub/app/static/index.html.bak_v306', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Update version
text = text.replace('var TARGET_VER = "v3.0.6";', 'var TARGET_VER = "v3.1.0";')
text = text.replace('var TARGET_VER = "v3.0.5";', 'var TARGET_VER = "v3.1.0";')

# 2. Update Header buttons
old_header_pattern = r'<div class="badge-pill"[^>]*onclick="syncSystemTime\(\)"[^>]*>.*?</div>\s*<button class="btn-allhouse-header".*?<button class="btn-memory-header"[^>]*>.*?</button>'

new_header_buttons = '''<div class="badge-pill" style="cursor: pointer; background: rgba(56, 189, 248, 0.1); border-color: rgba(56, 189, 248, 0.35);" onclick="syncSystemTime()" title="Bấm để đồng bộ giờ thực GMT+7 xuống toàn bộ màn hình ESP32">
                    <span style="font-size: 13px;">🕒</span>
                    <span id="headerClockText" style="color: #38bdf8; font-weight: 700;">--:--:--</span>
                    <span style="font-size: 10px; background: #0284c7; color: white; padding: 1px 6px; border-radius: 4px; font-weight: 700;">Đồng Bộ Giờ</span>
                </div>

                <!-- 1. HỒ SƠ & TRÍ NHỚ (Gộp Vân Giọng & Trí Nhớ Nala) -->
                <button type="button" class="btn-hub-nav" onclick="openUserProfileMemoryModal()" style="background: linear-gradient(135deg, #06b6d4, #0284c7); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.35); transition: all 0.2s;">
                    👤 Hồ Sơ &amp; Trí Nhớ
                </button>

                <!-- 2. TỰ ĐỘNG HÓA NGỮ CẢNH (FSM Radar/Lux & Rule Engine) -->
                <button type="button" class="btn-hub-nav" onclick="openLivingContextAutomationModal()" style="background: linear-gradient(135deg, #10b981, #059669); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35); transition: all 0.2s;">
                    🌙 Tự Động Hóa Ngữ Cảnh
                </button>

                <!-- 3. GIAO TIẾP & LỊCH SỬ (Intercom & Voice History) -->
                <button type="button" class="btn-hub-nav" onclick="openCommunicationModal()" style="background: linear-gradient(135deg, #f59e0b, #d97706); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35); transition: all 0.2s;">
                    🎙️ Giao Tiếp &amp; Lịch Sử
                </button>

                <!-- LIVE CALL INDICATOR -->
                <span id="headerActiveCallPill" style="display: none; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; color: #fca5a5; font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 8px; cursor: pointer; align-items: center; gap: 6px; animation: pulse 1.5s infinite;" onclick="openCommunicationModal('intercom')">
                    <span style="display: inline-block; width: 8px; height: 8px; background: #ef4444; border-radius: 50%;"></span>
                    <span id="headerActiveCallText">Đàm Thoại Rảnh Tay</span>
                </span>

                <!-- LIVE SPEAKER BADGE -->
                <span id="headerSpeakerBadge" style="display: none; background: rgba(6, 182, 212, 0.2); border: 1px solid #06b6d4; color: #38bdf8; font-size: 11px; font-weight: 700; padding: 5px 12px; border-radius: 8px; align-items: center; gap: 6px; cursor: pointer;" onclick="openUserProfileMemoryModal('members')">
                    <span style="display: inline-block; width: 7px; height: 7px; background: #06b6d4; border-radius: 50%; animation: pulse 1.5s infinite;"></span>
                    <span>Đang nói: </span><b id="headerSpeakerName">--</b>
                </span>

                <!-- 4. CÀI ĐẶT KỸ THUẬT (Home Assistant, Voice AI, OTA Firmware) -->
                <button type="button" class="btn-hub-nav" onclick="openSystemSettingsModal()" style="background: linear-gradient(135deg, #6366f1, #4f46e5); border: none; color: white; padding: 7px 15px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35); transition: all 0.2s;">
                    ⚙️ Cài Đặt Kỹ Thuật
                </button>'''

hm = re.search(old_header_pattern, text, re.DOTALL)
assert hm is not None, "Failed to match old_header_pattern"
text = text[:hm.start()] + new_header_buttons + text[hm.end():]

# Helper to extract inner modal content (body + footer)
def extract_modal_inner(start_id, next_id):
    chunk = text[text.find(f'id="{start_id}"'):text.find(f'id="{next_id}"')]
    body_match = re.search(r'(<div class="modal-body".*?)(?=\s*</div>\s*</div>\s*<!--|\s*</div>\s*</div>\s*<div|\Z)', chunk, re.DOTALL)
    if body_match:
        return body_match.group(1).strip()
    return ""

ha_inner = extract_modal_inner('haConfigModal', 'otaManagerModal')
ota_inner = extract_modal_inner('otaManagerModal', 'intercomModal')
intercom_inner = extract_modal_inner('intercomModal', 'historyModal')
history_inner = extract_modal_inner('historyModal', 'voiceprintModal')
ai_inner = extract_modal_inner('aiConfigModal', 'nalaMemoryModal')
mem_chunk = text[text.find('id="nalaMemoryModal"'):text.find('id="allHouseConfigModal"')]
mem_inner_match = re.search(r'(<!-- Metric Badges & Action Bar -->.*?<div class="modal-body".*?</div>)', mem_chunk, re.DOTALL)
mem_inner = mem_inner_match.group(1).strip() if mem_inner_match else ""

# Extract voiceprint tabs
vp_chunk = text[text.find('id="voiceprintModal"'):text.find('id="automationEditorModal"')]
def extract_vp_tab(tab_id, next_tab_id):
    start = vp_chunk.find(f'id="{tab_id}"')
    if start == -1: return ""
    div_start = vp_chunk.rfind('<div', 0, start)
    if next_tab_id:
        end = vp_chunk.find(f'id="{next_tab_id}"')
        div_end = vp_chunk.rfind('<!-- TAB', 0, end)
        if div_end == -1: div_end = vp_chunk.rfind('<div', 0, end)
        return vp_chunk[div_start:div_end].strip()
    else:
        end = vp_chunk.find('class="modal-footer"')
        div_end = vp_chunk.rfind('</div>', 0, end)
        return vp_chunk[div_start:div_end].strip()

t_speakers = extract_vp_tab('tab_vp_speakers', 'tab_vp_enroll')
t_enroll = extract_vp_tab('tab_vp_enroll', 'tab_vp_history')
t_history = extract_vp_tab('tab_vp_history', 'tab_vp_test')
t_test = extract_vp_tab('tab_vp_test', 'tab_vp_context')
t_context = extract_vp_tab('tab_vp_context', None)

print("Extracted all inner contents successfully!")

# Build the 4 new unified modals
modal_1_upm = f'''    <!-- ======================================================================= -->
    <!-- MODAL 1: HỒ SƠ THÀNH VIÊN & TRÍ NHỚ NALA (PROFILES & MEMORY HUB)       -->
    <!-- ======================================================================= -->
    <div class="modal-overlay" id="userProfileMemoryModal" onclick="if(event.target===this) closeUserProfileMemoryModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 920px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
            <div class="modal-header" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-bottom: 1px solid #334155; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="modal-title" style="display: flex; align-items: center; gap: 8px;">
                        <span>👤 Hồ Sơ Thành Viên &amp; Trí Nhớ Nala</span>
                        <span style="background: rgba(6, 182, 212, 0.2); color: #38bdf8; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(6, 182, 212, 0.4);">XiaoZhi CAM++ • Adaptive Memory</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        Hợp nhất Vân giọng sinh trắc học &amp; Trí nhớ tự học biệt danh, thói quen sinh hoạt cho từng thành viên
                    </div>
                </div>
                <button class="btn-close" onclick="closeUserProfileMemoryModal()">&times;</button>
            </div>

            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_upm_members_btn" onclick="switchUserProfileMemoryTab('members')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    👥 Danh Sách Thành Viên (<span id="vpSpeakersCount">0</span>)
                </div>
                <div class="wizard-tab" id="tab_upm_voiceprint_btn" onclick="switchUserProfileMemoryTab('voiceprint')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎙️ Huấn Luyện Vân Giọng (XiaoZhi)
                </div>
                <div class="wizard-tab" id="tab_upm_memory_btn" onclick="switchUserProfileMemoryTab('memory')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🧠 Trí Nhớ &amp; Thói Quen Tự Học
                </div>
                <div class="wizard-tab" id="tab_upm_test_btn" onclick="switchUserProfileMemoryTab('test')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🧪 Thử Nghiệm Nhận Diện
                </div>
            </div>

            <div class="modal-body" style="padding: 24px; overflow-y: auto; flex: 1;">
                <!-- TAB 1: MEMBERS -->
                <div id="tab_upm_members" style="display: block;">
                    {t_speakers}
                </div>

                <!-- TAB 2: VOICEPRINT (Live Multi-Slot & History Multi-Select) -->
                <div id="tab_upm_voiceprint" style="display: none;">
                    <div style="display: flex; gap: 10px; margin-bottom: 16px; border-bottom: 1px solid #334155; padding-bottom: 12px;">
                        <button type="button" id="sub_vp_live_btn" onclick="switchVoiceprintSubMode('live')" style="background: #0284c7; color: white; border: none; padding: 7px 16px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer;">
                            🎙️ Thu Âm Đa Mẫu Trực Tiếp
                        </button>
                        <button type="button" id="sub_vp_hist_btn" onclick="switchVoiceprintSubMode('history')" style="background: #1e293b; color: #94a3b8; border: 1px solid #475569; padding: 7px 16px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer;">
                            📜 Chọn Từ Lịch Sử Giọng Nói
                        </button>
                    </div>
                    <div id="sub_vp_live_panel" style="display: block;">
                        {t_enroll}
                    </div>
                    <div id="sub_vp_hist_panel" style="display: none;">
                        {t_history}
                    </div>
                </div>

                <!-- TAB 3: MEMORY -->
                <div id="tab_upm_memory" style="display: none;">
                    {mem_inner}
                </div>

                <!-- TAB 4: TEST IDENTIFICATION -->
                <div id="tab_upm_test" style="display: none;">
                    {t_test}
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeUserProfileMemoryModal()">Đóng</button>
            </div>
        </div>
    </div>'''

modal_2_lca = f'''    <!-- ======================================================================= -->
    <!-- MODAL 2: TỰ ĐỘNG HÓA NGỮ CẢNH SỐNG & FSM (LIVING CONTEXT & AUTOMATION)  -->
    <!-- ======================================================================= -->
    <div class="modal-overlay" id="livingContextAutomationModal" onclick="if(event.target===this) closeLivingContextAutomationModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 880px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
            <div class="modal-header" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-bottom: 1px solid #334155; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="modal-title" style="display: flex; align-items: center; gap: 8px;">
                        <span>🌙 Tự Động Hóa Ngữ Cảnh Sống &amp; Kịch Bản FSM</span>
                        <span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(16, 185, 129, 0.4);">Sensor Fusion • Rule Engine</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        Hợp nhất Radar nhịp thở LD2410 + Cảm biến ánh sáng Lux + Giờ GMT+7 + Kịch bản thông minh phi tuyến tính
                    </div>
                </div>
                <button class="btn-close" onclick="closeLivingContextAutomationModal()">&times;</button>
            </div>

            <div class="modal-body" style="padding: 24px; overflow-y: auto; flex: 1;">
                {t_context}
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeLivingContextAutomationModal()">Đóng</button>
            </div>
        </div>
    </div>'''

modal_3_comm = f'''    <!-- ======================================================================= -->
    <!-- MODAL 3: TRUNG TÂM GIAO TIẾP & LỊCH SỬ (INTERCOM & VOICE HISTORY HUB)   -->
    <!-- ======================================================================= -->
    <div class="modal-overlay" id="communicationModal" onclick="if(event.target===this) closeCommunicationModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 880px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
            <div class="modal-header" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-bottom: 1px solid #334155; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="modal-title" style="display: flex; align-items: center; gap: 8px;">
                        <span>🎙️ Trung Tâm Giao Tiếp &amp; Lịch Sử Đàm Thoại</span>
                        <span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.4);">Hands-Free Intercom • Voice History</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        Đàm thoại rảnh tay liên phòng 2 chiều + Nhật ký nhận dạng giọng nói STT &amp; File ghi âm
                    </div>
                </div>
                <button class="btn-close" onclick="closeCommunicationModal()">&times;</button>
            </div>

            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_comm_intercom_btn" onclick="switchCommunicationTab('intercom')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎙️ Đàm Thoại Intercom Rảnh Tay
                </div>
                <div class="wizard-tab" id="tab_comm_history_btn" onclick="switchCommunicationTab('history')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    💬 Lịch Sử Giọng Nói &amp; STT
                </div>
            </div>

            <div class="modal-body" style="padding: 0; overflow-y: auto; flex: 1;">
                <div id="tab_comm_intercom" style="display: block;">
                    {intercom_inner}
                </div>
                <div id="tab_comm_history" style="display: none;">
                    {history_inner}
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeCommunicationModal()">Đóng</button>
            </div>
        </div>
    </div>'''

modal_4_sys = f'''    <!-- ======================================================================= -->
    <!-- MODAL 4: CÀI ĐẶT KỸ THUẬT & PHẦN CỨNG (SYSTEM SETTINGS & HARDWARE HUB)  -->
    <!-- ======================================================================= -->
    <div class="modal-overlay" id="systemSettingsModal" onclick="if(event.target===this) closeSystemSettingsModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 880px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
            <div class="modal-header" style="background: linear-gradient(135deg, #0f172a, #1e293b); border-bottom: 1px solid #334155; padding: 18px 24px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div class="modal-title" style="display: flex; align-items: center; gap: 8px;">
                        <span>⚙️ Trung Tâm Cài Đặt Kỹ Thuật &amp; Phần Cứng</span>
                        <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(99, 102, 241, 0.4);">HA Pi 5 • Voice AI • OTA</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                        Quản lý kết nối Home Assistant, cấu hình mô hình Voice AI (LLM / STT / TTS) và nạp firmware OTA cho ESP32
                    </div>
                </div>
                <button class="btn-close" onclick="closeSystemSettingsModal()">&times;</button>
            </div>

            <!-- Tab Headers -->
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
            </div>

            <div class="modal-body" style="padding: 0; overflow-y: auto; flex: 1;">
                <div id="tab_sys_ha" style="display: block;">
                    {ha_inner}
                </div>
                <div id="tab_sys_ai" style="display: none;">
                    {ai_inner}
                </div>
                <div id="tab_sys_ota" style="display: none;">
                    {ota_inner}
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeSystemSettingsModal()">Đóng</button>
            </div>
        </div>
    </div>'''

# Now let's replace the old modals in text:
# 1. From haConfigModal to before automationEditorModal:
# It spans haConfigModal, otaManagerModal, intercomModal, historyModal, voiceprintModal
part1_start = text.find('id="haConfigModal"')
div_part1_start = text.rfind('<div', 0, part1_start)

part1_end = text.find('id="automationEditorModal"')
div_part1_end = text.rfind('<!--', 0, part1_end)
if div_part1_end == -1: div_part1_end = text.rfind('<div', 0, part1_end)

# In part 1, replace with modal_4_sys + modal_3_comm + modal_1_upm + modal_2_lca
replacement_part1 = modal_1_upm + "\n\n" + modal_2_lca + "\n\n" + modal_3_comm + "\n\n" + modal_4_sys + "\n\n"
text = text[:div_part1_start] + replacement_part1 + text[div_part1_end:]

# 2. Now handle aiConfigModal and nalaMemoryModal
# From aiConfigModal to before allHouseConfigModal:
part2_start = text.find('id="aiConfigModal"')
div_part2_start = text.rfind('<div', 0, part2_start)

part2_end = text.find('id="allHouseConfigModal"')
div_part2_end = text.rfind('<!--', 0, part2_end)
if div_part2_end == -1: div_part2_end = text.rfind('<div', 0, part2_end)

# Since ai and memory are now inside systemSettingsModal and userProfileMemoryModal, remove them here!
text = text[:div_part2_start] + "<!-- aiConfigModal & nalaMemoryModal moved to unified hubs -->\n" + text[div_part2_end:]

# 3. Add Javascript controller functions & Backward compatibility bridges
js_controllers = '''
// =========================================================================
// 4 UNIFIED HUBS CONTROLLERS & BACKWARD COMPATIBILITY BRIDGES
// =========================================================================

// HUB 1: HỒ SƠ THÀNH VIÊN & TRÍ NHỚ NALA
function openUserProfileMemoryModal(tab = 'members') {
    const modal = document.getElementById('userProfileMemoryModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    switchUserProfileMemoryTab(tab);
}
function closeUserProfileMemoryModal() {
    const modal = document.getElementById('userProfileMemoryModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}
function switchUserProfileMemoryTab(tabId) {
    const tabs = ['members', 'voiceprint', 'memory', 'test'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_upm_${t}_btn`);
        const content = document.getElementById(`tab_upm_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'members') loadVoiceprintSpeakers();
    if (tabId === 'voiceprint') {
        loadHistoryForVoiceprint();
    }
    if (tabId === 'memory') loadMemoryData();
}

function switchVoiceprintSubMode(mode) {
    const liveBtn = document.getElementById('sub_vp_live_btn');
    const histBtn = document.getElementById('sub_vp_hist_btn');
    const livePanel = document.getElementById('sub_vp_live_panel');
    const histPanel = document.getElementById('sub_vp_hist_panel');
    if (mode === 'live') {
        if (liveBtn) { liveBtn.style.background = '#0284c7'; liveBtn.style.color = '#fff'; }
        if (histBtn) { histBtn.style.background = '#1e293b'; histBtn.style.color = '#94a3b8'; }
        if (livePanel) livePanel.style.display = 'block';
        if (histPanel) histPanel.style.display = 'none';
    } else {
        if (histBtn) { histBtn.style.background = '#0284c7'; histBtn.style.color = '#fff'; }
        if (liveBtn) { liveBtn.style.background = '#1e293b'; liveBtn.style.color = '#94a3b8'; }
        if (histPanel) histPanel.style.display = 'block';
        if (livePanel) livePanel.style.display = 'none';
        loadHistoryForVoiceprint();
    }
}

// HUB 2: TỰ ĐỘNG HÓA NGỮ CẢNH SỐNG & FSM
function openLivingContextAutomationModal() {
    const modal = document.getElementById('livingContextAutomationModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    loadLivingContextDashboard();
    loadAutomationRules();
}
function closeLivingContextAutomationModal() {
    const modal = document.getElementById('livingContextAutomationModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

// HUB 3: GIAO TIẾP & LỊCH SỬ ĐÀM THOẠI
function openCommunicationModal(tab = 'intercom') {
    const modal = document.getElementById('communicationModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    switchCommunicationTab(tab);
}
function closeCommunicationModal() {
    const modal = document.getElementById('communicationModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}
function switchCommunicationTab(tabId) {
    const tabs = ['intercom', 'history'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_comm_${t}_btn`);
        const content = document.getElementById(`tab_comm_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'history') {
        loadHistorySettings();
        loadHistoryData();
    }
}

// HUB 4: CÀI ĐẶT KỸ THUẬT & PHẦN CỨNG
function openSystemSettingsModal(tab = 'ha') {
    const modal = document.getElementById('systemSettingsModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    switchSystemSettingsTab(tab);
}
function closeSystemSettingsModal() {
    const modal = document.getElementById('systemSettingsModal');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}
function switchSystemSettingsTab(tabId) {
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
}

// BACKWARD COMPATIBILITY BRIDGES
function openHAConfigModal() { openSystemSettingsModal('ha'); }
function closeHAConfigModal() { closeSystemSettingsModal(); }
function openOTAManagerModal() { openSystemSettingsModal('ota'); }
function closeOTAManagerModal() { closeSystemSettingsModal(); }
function openAIConfigModal() { openSystemSettingsModal('ai'); }
function closeAIConfigModal() { closeSystemSettingsModal(); }
function openIntercomModal() { openCommunicationModal('intercom'); }
function closeIntercomModal() { closeCommunicationModal(); }
function openHistoryModal() { openCommunicationModal('history'); }
function closeHistoryModal() { closeCommunicationModal(); }
function openVoiceprintModal(tab = 'members') {
    if (tab === 'context') {
        openLivingContextAutomationModal();
    } else {
        openUserProfileMemoryModal(tab === 'enroll' ? 'voiceprint' : tab);
    }
}
function closeVoiceprintModal() { closeUserProfileMemoryModal(); }
function openMemoryModal() { openUserProfileMemoryModal('memory'); }
function closeMemoryModal() { closeUserProfileMemoryModal(); }
'''

# Insert js_controllers before </script></body>
script_end = text.rfind('</script>')
text = text[:script_end] + "\n" + js_controllers + "\n" + text[script_end:]

# Write to destination
with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("✅ Successfully built unified index.html v3.1.0!")
