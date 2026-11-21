import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

print("Original text length:", len(text))

# -------------------------------------------------------------------------
# FIX 1: livingContextAutomationModal
# Add tabs: [🧭 Giám Sát Ngữ Cảnh Sống & Radar FSM] and [⚙️ Kịch Bản Tự Động Hóa (Rule Engine)]
# -------------------------------------------------------------------------
old_lc_modal_start = text.find('id="livingContextAutomationModal"')
old_lc_modal_end = text.find('id="communicationModal"')

new_lc_modal_content = '''id="livingContextAutomationModal" onclick="if(event.target===this) closeLivingContextAutomationModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 900px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
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

            <!-- Tab Headers -->
            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_lc_fsm_btn" onclick="switchLivingContextTab('fsm')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🧭 Giám Sát FSM &amp; Radar LD2410
                </div>
                <div class="wizard-tab" id="tab_lc_rules_btn" onclick="switchLivingContextTab('rules')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    ⚙️ Kịch Bản Tự Động Hóa (Rule Engine)
                </div>
            </div>

            <div class="modal-body" style="padding: 24px; overflow-y: auto; flex: 1;">
                <!-- TAB 1: FSM & Radar Presence Monitoring -->
                <div id="tab_lc_fsm" style="display: block;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                        <div style="font-size: 13px; color: #94a3b8;">
                            Trạng thái FSM hợp nhất Radar nhịp thở + Quang trở Lux + Giờ GMT+7 + Vân giọng từng phòng:
                        </div>
                        <button onclick="loadLivingContextDashboard()" style="background: transparent; border: 1px solid #334155; color: #94a3b8; border-radius: 6px; padding: 4px 10px; font-size: 11px; cursor: pointer;">
                            🔄 Làm mới
                        </button>
                    </div>
                    <div id="vpContextRoomsGrid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; margin-bottom: 24px;">
                        <!-- Rendered by JS -->
                    </div>
                </div>

                <!-- TAB 2: Rule Engine -->
                <div id="tab_lc_rules" style="display: none;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
                        <div>
                            <h4 style="margin: 0 0 4px 0; color: #f8fafc; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                                <span>⚙️ Kịch Bản Tự Động Hóa Phi Tuyến Tính (Rule Engine)</span>
                                <span style="font-size: 11px; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 8px; border-radius: 6px;">Tùy Biến 100%</span>
                            </h4>
                            <div style="font-size: 12px; color: #94a3b8;">
                                Toàn quyền tự do tạo mới, tùy biến điều kiện cảm biến, khung giờ và hành động thiết bị:
                            </div>
                        </div>
                        <button type="button" onclick="openAutomationEditorModal()" style="background: linear-gradient(135deg, #06b6d4, #0284c7); border: none; color: white; padding: 8px 16px; border-radius: 8px; font-weight: 700; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.35);">
                            ➕ Tạo Kịch Bản Mới
                        </button>
                    </div>
                    <div id="vpAutomationRulesList">
                        <!-- Rendered by JS -->
                    </div>
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeLivingContextAutomationModal()">Đóng</button>
            </div>
        </div>
    </div>\n\n    <!-- ======================================================================= -->\n    <!-- MODAL 3: TRUNG TÂM GIAO TIẾP & LỊCH SỬ (INTERCOM & VOICE HISTORY HUB)   -->\n    <!-- ======================================================================= -->\n    <div class="modal-overlay" '''

text = text[:old_lc_modal_start] + new_lc_modal_content + text[old_lc_modal_end:]

# -------------------------------------------------------------------------
# FIX 2: communicationModal
# Restore full Intercom + full History bodies
# -------------------------------------------------------------------------
with open('scratch/intercomModal_original.html', 'r', encoding='utf-8') as f:
    orig_intercom = f.read()

with open('scratch/historyModal_original.html', 'r', encoding='utf-8') as f:
    orig_hist = f.read()

# Extract inner bodies
intercom_mb_start = orig_intercom.find('<div class="modal-body"')
intercom_mb_end = orig_intercom.find('<div class="modal-footer"')
intercom_inner = orig_intercom[intercom_mb_start:intercom_mb_end]

hist_mb_start = orig_hist.find('<div class="modal-body"')
hist_mb_end = orig_hist.find('<div class="modal-footer"')
hist_inner = orig_hist[hist_mb_start:hist_mb_end]

old_comm_start = text.find('id="communicationModal"')
old_comm_end = text.find('id="systemSettingsModal"')

# Active calls banner inside intercom tab
active_calls_banner = '''<!-- Cuộc Gọi Đàm Thoại Rảnh Tay Đang Diễn Ra (Active Calls Banner) -->
                <div id="activeIntercomCallsContainer" style="display: none; background: rgba(220, 38, 38, 0.15); border: 1px solid #ef4444; border-radius: 12px; padding: 14px 18px; margin-bottom: 20px;">
                    <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="width: 10px; height: 10px; background: #ef4444; border-radius: 50%; display: inline-block;"></span>
                            <span style="font-weight: 700; font-size: 13px; color: #fca5a5;">📞 ĐANG ĐÀM THOẠI RẢNH TAY:</span>
                            <span id="activeCallInfoLabel" style="font-size: 13px; font-weight: 700; color: #fff;">[Phòng] ⇄ [Phòng]</span>
                        </div>
                        <button onclick="hangupCurrentCall()" style="padding: 6px 14px; background: #dc2626; color: #fff; border: none; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; transition: background 0.2s;">
                            🛑 Ngắt Máy Từ Xa
                        </button>
                    </div>
                </div>'''

new_comm_modal = '''id="communicationModal" onclick="if(event.target===this) closeCommunicationModal()" style="display: none; align-items: center; justify-content: center; z-index: 10001;">
        <div class="modal-box" style="max-width: 900px; width: 95%; max-height: 90vh; display: flex; flex-direction: column; background: #0f172a; border: 1px solid #334155; border-radius: 16px; box-shadow: 0 25px 60px rgba(0,0,0,0.85); overflow: hidden;">
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
                <!-- TAB 1: Intercom -->
                <div id="tab_comm_intercom" style="display: block;">
                    <div class="modal-body" style="padding: 24px;">
                        ''' + active_calls_banner + '''
                        ''' + intercom_inner[intercom_inner.find('>')+1:] + '''
                    </div>
                </div>

                <!-- TAB 2: History -->
                <div id="tab_comm_history" style="display: none;">
                    ''' + hist_inner + '''
                </div>
            </div>

            <div class="modal-footer" style="padding: 16px 24px; background: #182234; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end;">
                <button type="button" class="btn-cancel" onclick="closeCommunicationModal()">Đóng</button>
            </div>
        </div>
    </div>\n\n    <!-- ======================================================================= -->\n    <!-- MODAL 4: CÀI ĐẶT KỸ THUẬT & PHẦN CỨNG (SYSTEM SETTINGS & HARDWARE HUB)  -->\n    <!-- ======================================================================= -->\n    <div class="modal-overlay" '''

text = text[:old_comm_start] + new_comm_modal + text[old_comm_end:]

# -------------------------------------------------------------------------
# FIX 3: JavaScript function updates
# Ensure switchLivingContextTab, switchCommunicationTab, switchSystemSettingsTab
# call the EXACT real functions!
# -------------------------------------------------------------------------

# Replace switchSystemSettingsTab
old_sys_fn_pattern = r'function switchSystemSettingsTab\(tabId\) \{[\s\S]*?\}'
new_sys_fn = '''function switchSystemSettingsTab(tabId) {
    const tabs = ['role', 'ai', 'ha', 'ota'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_sys_${t}_btn`);
        const content = document.getElementById(`tab_sys_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'role') loadXiaoZhiVoiceRole();
    if (tabId === 'ai') openAIConfigModal();
    if (tabId === 'ha') openHAConfigModal();
    if (tabId === 'ota') {
        if (typeof loadOtaStatus === 'function') loadOtaStatus();
        if (typeof renderOtaTrackerList === 'function') renderOtaTrackerList();
    }
}'''
text = re.sub(old_sys_fn_pattern, new_sys_fn, text, count=1)

# Add or replace switchLivingContextTab
old_lc_fn = '''function openLivingContextAutomationModal() {
    const modal = document.getElementById('livingContextAutomationModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    loadLivingContextDashboard();
    loadAutomationRules();
}'''

new_lc_fn = '''function openLivingContextAutomationModal(tab = 'fsm') {
    const modal = document.getElementById('livingContextAutomationModal');
    if (!modal) return;
    modal.style.display = 'flex';
    modal.classList.add('active');
    switchLivingContextTab(tab);
}

function switchLivingContextTab(tabId) {
    const tabs = ['fsm', 'rules'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_lc_${t}_btn`);
        const content = document.getElementById(`tab_lc_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'fsm') {
        if (typeof loadLivingContextDashboard === 'function') loadLivingContextDashboard();
    }
    if (tabId === 'rules') {
        if (typeof loadAutomationRules === 'function') loadAutomationRules();
    }
}'''

text = text.replace(old_lc_fn, new_lc_fn)

# Update switchCommunicationTab
old_comm_fn_pattern = r'function switchCommunicationTab\(tabId\) \{[\s\S]*?\}'
new_comm_fn = '''function switchCommunicationTab(tabId) {
    const tabs = ['intercom', 'history'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_comm_${t}_btn`);
        const content = document.getElementById(`tab_comm_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'intercom') {
        if (typeof renderIntercomTargets === 'function') renderIntercomTargets();
        if (typeof attachPttEvents === 'function') attachPttEvents();
        if (typeof updateActiveIntercomCallsBanner === 'function') updateActiveIntercomCallsBanner();
    }
    if (tabId === 'history') {
        if (typeof loadHistorySettings === 'function') loadHistorySettings();
        if (typeof loadHistoryData === 'function') loadHistoryData();
    }
}'''
text = re.sub(old_comm_fn_pattern, new_comm_fn, text, count=1)

# Wire switchVoiceprintTab bridge
old_switch_vp_pattern = r'function switchVoiceprintTab\(tabId\) \{[\s\S]*?\}'
new_switch_vp = '''function switchVoiceprintTab(tabId) {
    if (tabId === 'speakers') {
        switchUserProfileMemoryTab('members');
    } else if (tabId === 'enroll') {
        switchUserProfileMemoryTab('voiceprint');
        if (typeof switchVoiceprintSubMode === 'function') switchVoiceprintSubMode('live');
    } else if (tabId === 'history') {
        switchUserProfileMemoryTab('voiceprint');
        if (typeof switchVoiceprintSubMode === 'function') switchVoiceprintSubMode('history');
    } else if (tabId === 'test') {
        switchUserProfileMemoryTab('test');
    } else if (tabId === 'context') {
        openLivingContextAutomationModal('fsm');
    }
}'''
text = re.sub(old_switch_vp_pattern, new_switch_vp, text, count=1)

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved updated index.html successfully! New length:", len(text))
