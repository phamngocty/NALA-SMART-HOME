import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update TARGET_VER to v3.0.6
html = html.replace('var TARGET_VER = "v3.0.5";', 'var TARGET_VER = "v3.0.6";')

# 2. Update wizard-tabs
old_tabs = '''            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px;">
                <div class="wizard-tab active" id="tab_vp_speakers_btn" onclick="switchVoiceprintTab('speakers')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    👥 Hồ Sơ Người Dùng (<span id="vpSpeakersCount">0</span>)
                </div>
                <div class="wizard-tab" id="tab_vp_enroll_btn" onclick="switchVoiceprintTab('enroll')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎙️ Thu Âm Đăng Ký Mới
                </div>
                <div class="wizard-tab" id="tab_vp_test_btn" onclick="switchVoiceprintTab('test')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🧪 Thử Nghiệm So Khớp
                </div>
                <div class="wizard-tab" id="tab_vp_context_btn" onclick="switchVoiceprintTab('context')" style="cursor: pointer; padding: 12px 18px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🌙 Ngữ Cảnh Sống &amp; Kịch Bản FSM
                </div>
            </div>'''

new_tabs = '''            <div class="wizard-tabs" style="border-bottom: 1px solid #334155; margin-bottom: 0; background: #0f172a; padding: 0 20px; display: flex; flex-wrap: wrap;">
                <div class="wizard-tab active" id="tab_vp_speakers_btn" onclick="switchVoiceprintTab('speakers')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    👥 Hồ Sơ Người Dùng (<span id="vpSpeakersCount">0</span>)
                </div>
                <div class="wizard-tab" id="tab_vp_enroll_btn" onclick="switchVoiceprintTab('enroll')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🎙️ Thu Trực Tiếp (Đa Mẫu)
                </div>
                <div class="wizard-tab" id="tab_vp_history_btn" onclick="switchVoiceprintTab('history')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    📜 Chọn Từ Lịch Sử Giọng Nói
                </div>
                <div class="wizard-tab" id="tab_vp_test_btn" onclick="switchVoiceprintTab('test')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🧪 Thử Nghiệm So Khớp
                </div>
                <div class="wizard-tab" id="tab_vp_context_btn" onclick="switchVoiceprintTab('context')" style="cursor: pointer; padding: 12px 16px; font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 6px;">
                    🌙 Ngữ Cảnh Sống &amp; Kịch Bản FSM
                </div>
            </div>'''

assert old_tabs in html, "Could not find old_tabs"
html = html.replace(old_tabs, new_tabs, 1)

# 3. Replace tab_vp_enroll and insert tab_vp_history
old_tab_vp_enroll = '''                <!-- TAB 2: THU ÂM ĐĂNG KÝ TRỰC TIẾP -->
                <div id="tab_vp_enroll" style="display: none;">
                    <div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; max-width: 600px; margin: 0 auto;">
                        <h4 style="margin: 0 0 12px 0; color: #f8fafc; font-size: 15px;">🎙️ Đăng Ký Mẫu Giọng Từ Trình Duyệt Web</h4>
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; font-size: 13px; color: #94a3b8; margin-bottom: 6px;">Tên thành viên / Người nói:</label>
                            <input type="text" id="vpEnrollName" placeholder="Ví dụ: Anh Tý, Mẹ, Bố, Linh..." style="width: 100%; box-sizing: border-box; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px;">
                        </div>

                        <div style="background: rgba(30, 41, 59, 0.7); border: 1px dashed #475569; border-radius: 10px; padding: 18px; text-align: center; margin-bottom: 18px;">
                            <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 12px;">
                                💡 Nhấn nút bên dưới và nói tự nhiên 3-5 giây:<br>
                                <em style="color: #38bdf8;">"Xin chào Nala, tôi tên là [Tên], hãy ghi nhớ giọng của tôi nhé."</em>
                            </div>

                            <div id="vpRecordStatus" style="font-size: 14px; font-weight: 700; color: #94a3b8; margin-bottom: 12px;">Chưa bắt đầu thu âm</div>

                            <div style="display: flex; justify-content: center; gap: 12px; align-items: center;">
                                <button type="button" id="vpBtnRecord" onclick="toggleBrowserRecording()" style="background: #ef4444; color: white; border: none; padding: 10px 22px; border-radius: 8px; font-weight: 700; font-size: 14px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.35);">
                                    🔴 Bắt Đầu Thu Âm
                                </button>
                            </div>

                            <div id="vpAudioPreviewBox" style="display: none; margin-top: 16px;">
                                <audio id="vpAudioPreview" controls style="width: 100%; height: 36px;"></audio>
                            </div>
                        </div>

                        <div style="display: flex; justify-content: flex-end; gap: 10px;">
                            <button type="button" id="vpBtnSave" onclick="saveBrowserVoiceprint()" disabled style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; opacity: 0.5;">
                                💾 Lưu Vân Giọng Vào Hệ Thống
                            </button>
                        </div>
                    </div>
                </div>'''

new_tabs_content = '''                <!-- TAB 2: THU ÂM ĐĂNG KÝ TRỰC TIẾP (ĐA MẪU XIAOZHI) -->
                <div id="tab_vp_enroll" style="display: none;">
                    <div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 20px; max-width: 680px; margin: 0 auto;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <h4 style="margin: 0; color: #f8fafc; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                                <span>🎙️ Đăng Ký Mẫu Giọng Trực Tiếp (Cơ Chế XiaoZhi Centroid)</span>
                            </h4>
                            <span style="font-size: 11px; background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 3px 8px; border-radius: 6px; font-weight: 700;">Đa Mẫu Chuẩn Xác Cao</span>
                        </div>
                        
                        <div style="background: rgba(30, 41, 59, 0.6); border: 1px solid #334155; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #94a3b8; margin-bottom: 16px; line-height: 1.5;">
                            💡 <strong style="color: #38bdf8;">Cơ chế giống XiaoZhi:</strong> Bạn có thể thu từ 1 đến 3 mẫu giọng khác nhau (mỗi mẫu 3-5 giây). Hệ thống sẽ trích xuất vector CAM++ của từng mẫu và tính vector trọng tâm trung bình (Centroid Averaging), giúp triệt tiêu tạp âm phòng và nhận diện chuẩn xác &gt;96%!
                        </div>

                        <div style="margin-bottom: 18px;">
                            <label style="display: block; font-size: 13px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Tên thành viên / Người nói:</label>
                            <input type="text" id="vpEnrollName" placeholder="Ví dụ: Anh Tý, Mẹ, Bố, Linh..." style="width: 100%; box-sizing: border-box; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px;">
                        </div>

                        <!-- 3 KHE THU ÂM (SAMPLE SLOTS) -->
                        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 18px;">
                            <!-- SLOT 1 -->
                            <div class="vp-slot-card" style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; min-width: 180px;">
                                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #3b82f6; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: white;">1</div>
                                    <div>
                                        <div style="font-weight: 700; font-size: 13px; color: #f8fafc;">Mẫu giọng 1 <span style="color: #f87171; font-size: 11px;">* (Bắt buộc)</span></div>
                                        <div id="vpSlotStatus_0" style="font-size: 11px; color: #94a3b8;">Chưa thu âm</div>
                                    </div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; justify-content: flex-end;">
                                    <audio id="vpSlotAudio_0" controls style="display: none; height: 32px; max-width: 180px;"></audio>
                                    <button type="button" id="vpSlotBtn_0" onclick="toggleSlotRecording(0)" style="background: #ef4444; color: white; border: none; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                        🔴 Thu Âm
                                    </button>
                                    <button type="button" id="vpSlotClear_0" onclick="clearSlotAudio(0)" style="display: none; background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 6px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;">
                                        🗑️
                                    </button>
                                </div>
                            </div>

                            <!-- SLOT 2 -->
                            <div class="vp-slot-card" style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; min-width: 180px;">
                                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #06b6d4; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: white;">2</div>
                                    <div>
                                        <div style="font-weight: 700; font-size: 13px; color: #f8fafc;">Mẫu giọng 2 <span style="color: #38bdf8; font-size: 11px;">(Khuyên dùng)</span></div>
                                        <div id="vpSlotStatus_1" style="font-size: 11px; color: #94a3b8;">Chưa thu âm</div>
                                    </div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; justify-content: flex-end;">
                                    <audio id="vpSlotAudio_1" controls style="display: none; height: 32px; max-width: 180px;"></audio>
                                    <button type="button" id="vpSlotBtn_1" onclick="toggleSlotRecording(1)" style="background: #0284c7; color: white; border: none; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                        🔴 Thu Âm
                                    </button>
                                    <button type="button" id="vpSlotClear_1" onclick="clearSlotAudio(1)" style="display: none; background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 6px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;">
                                        🗑️
                                    </button>
                                </div>
                            </div>

                            <!-- SLOT 3 -->
                            <div class="vp-slot-card" style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; min-width: 180px;">
                                    <div style="width: 28px; height: 28px; border-radius: 50%; background: #8b5cf6; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 13px; color: white;">3</div>
                                    <div>
                                        <div style="font-weight: 700; font-size: 13px; color: #f8fafc;">Mẫu giọng 3 <span style="color: #a78bfa; font-size: 11px;">(Khuyên dùng)</span></div>
                                        <div id="vpSlotStatus_2" style="font-size: 11px; color: #94a3b8;">Chưa thu âm</div>
                                    </div>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; justify-content: flex-end;">
                                    <audio id="vpSlotAudio_2" controls style="display: none; height: 32px; max-width: 180px;"></audio>
                                    <button type="button" id="vpSlotBtn_2" onclick="toggleSlotRecording(2)" style="background: #7c3aed; color: white; border: none; padding: 7px 14px; border-radius: 6px; font-weight: 700; font-size: 12px; cursor: pointer; display: flex; align-items: center; gap: 6px;">
                                        🔴 Thu Âm
                                    </button>
                                    <button type="button" id="vpSlotClear_2" onclick="clearSlotAudio(2)" style="display: none; background: transparent; border: 1px solid #475569; color: #94a3b8; padding: 6px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;">
                                        🗑️
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- CÂU GỢI Ý KHI THU -->
                        <div style="background: rgba(15, 23, 42, 0.8); border: 1px dashed #475569; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; font-size: 12px; color: #cbd5e1; text-align: center;">
                            💬 <em>Gợi ý câu nói: "Xin chào Nala, hãy ghi nhớ giọng của tôi để nhận diện nhé."</em>
                        </div>

                        <!-- NÚT LƯU VÂN GIỌNG -->
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                            <span id="vpSlotsRecordedSummary" style="font-size: 12px; color: #94a3b8;">Đã thu: 0/3 mẫu</span>
                            <button type="button" id="vpBtnSaveMulti" onclick="saveMultiSlotVoiceprint()" disabled style="background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 10px 22px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; opacity: 0.5; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35);">
                                💾 Huấn Luyện &amp; Lưu Vân Giọng (XiaoZhi)
                            </button>
                        </div>
                    </div>
                </div>

                <!-- TAB 3: CHỌN NHIỀU MẪU TỪ LỊCH SỬ GIỌNG NÓI (XIAOZHI STYLE) -->
                <div id="tab_vp_history" style="display: none;">
                    <div style="display: flex; flex-direction: column; gap: 16px;">
                        <div style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; padding: 16px 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px;">
                                <div>
                                    <h4 style="margin: 0; color: #f8fafc; font-size: 15px; display: flex; align-items: center; gap: 8px;">
                                        <span>📜 Chọn Mẫu Từ Lịch Sử Giọng Nói (Đa Chọn XiaoZhi)</span>
                                    </h4>
                                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">
                                        Chọn 2 - 5 đoạn ghi âm của cùng một người để Nala tự động gộp và tính vector trọng tâm Centroid.
                                    </div>
                                </div>
                                <button type="button" onclick="loadHistoryForVoiceprint()" style="background: #1e293b; border: 1px solid #475569; color: #cbd5e1; padding: 6px 14px; border-radius: 8px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;">
                                    🔄 Làm Mới Danh Sách
                                </button>
                            </div>

                            <!-- ACTION BAR: CHỌN TÊN VÀ NÚT HUẤN LUYỆN -->
                            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 250px;">
                                    <label style="font-size: 13px; font-weight: 700; color: #f8fafc; white-space: nowrap;">Tên thành viên:</label>
                                    <input type="text" id="vpHistTargetName" oninput="updateVpHistSelectedCount()" placeholder="Gõ tên hoặc chọn bên phải..." style="flex: 1; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 13px;">
                                    <select id="vpHistKnownSpeakersSelect" onchange="if(this.value) { document.getElementById('vpHistTargetName').value = this.value; updateVpHistSelectedCount(); }" style="background: #0f172a; border: 1px solid #475569; color: #94a3b8; padding: 8px 10px; border-radius: 6px; font-size: 12px; max-width: 140px;">
                                        <option value="">-- Có sẵn --</option>
                                    </select>
                                </div>

                                <div style="display: flex; align-items: center; gap: 12px;">
                                    <span style="font-size: 12px; color: #94a3b8;">
                                        Đã chọn: <strong id="vpHistSelectedCount" style="color: #38bdf8; font-size: 14px;">0</strong> mẫu
                                    </span>
                                    <button type="button" id="vpHistBtnEnroll" onclick="enrollSelectedHistoryRecordings()" disabled style="background: linear-gradient(135deg, #06b6d4, #0284c7); color: white; border: none; padding: 8px 18px; border-radius: 8px; font-weight: 700; font-size: 13px; cursor: pointer; opacity: 0.5; display: inline-flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(6, 182, 212, 0.35);">
                                        ✨ Gộp &amp; Huấn Luyện Vân Giọng
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- DANH SÁCH CÁC BẢN GHI ÂM TỪ LỊCH SỬ -->
                        <div id="vpHistListContainer" style="background: #0f172a; border: 1px solid #334155; border-radius: 12px; overflow: hidden; max-height: 450px; overflow-y: auto;">
                            <div style="padding: 30px; text-align: center; color: #94a3b8; font-size: 13px;">
                                Đang tải danh sách bản ghi âm lịch sử...
                            </div>
                        </div>
                    </div>
                </div>'''

assert old_tab_vp_enroll in html, "Could not find old_tab_vp_enroll"
html = html.replace(old_tab_vp_enroll, new_tabs_content, 1)

# 4. Update switchVoiceprintTab to include 'history'
old_switch_vp = '''function switchVoiceprintTab(tabId) {
    const tabs = ['speakers', 'enroll', 'test', 'context'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_vp_${t}_btn`);
        const content = document.getElementById(`tab_vp_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'speakers') loadVoiceprintSpeakers();
    if (tabId === 'context') {
        loadLivingContextDashboard();
        loadAutomationRules();
    }
}'''

new_switch_vp = '''function switchVoiceprintTab(tabId) {
    const tabs = ['speakers', 'enroll', 'history', 'test', 'context'];
    tabs.forEach(t => {
        const btn = document.getElementById(`tab_vp_${t}_btn`);
        const content = document.getElementById(`tab_vp_${t}`);
        if (btn) btn.classList.toggle('active', t === tabId);
        if (content) content.style.display = (t === tabId) ? 'block' : 'none';
    });
    if (tabId === 'speakers') loadVoiceprintSpeakers();
    if (tabId === 'history') loadHistoryForVoiceprint();
    if (tabId === 'context') {
        loadLivingContextDashboard();
        loadAutomationRules();
    }
}'''

assert old_switch_vp in html, "Could not find old_switch_vp"
html = html.replace(old_switch_vp, new_switch_vp, 1)

# 5. Add Javascript functions for multi-slot and history voiceprint
old_js_anchor = '''// =========================================================================
// XIAOZHI VOICEPRINT & LIVING CONTEXT AUTOMATION JAVASCRIPT
// =========================================================================
let vpMediaRecorder = null;
let vpAudioChunks = [];
let vpRecordedBlob = null;
let vpTestMediaRecorder = null;
let vpTestAudioChunks = [];'''

new_js_anchor = '''// =========================================================================
// XIAOZHI VOICEPRINT & LIVING CONTEXT AUTOMATION JAVASCRIPT
// =========================================================================
let vpMediaRecorder = null;
let vpAudioChunks = [];
let vpRecordedBlob = null;
let vpTestMediaRecorder = null;
let vpTestAudioChunks = [];

// XiaoZhi Multi-Slot Live Recording State
let vpSlots = [null, null, null]; // Recorded Blobs
let vpSlotRecorders = [null, null, null];
let vpSlotChunks = [[], [], []];
let vpActiveSlotIndex = -1;

// History selection state
let vpHistoryRecordsForVoiceprint = [];'''

assert old_js_anchor in html, "Could not find old_js_anchor"
html = html.replace(old_js_anchor, new_js_anchor, 1)

# 6. Add the new functions before toggleTestRecording
new_methods = '''
// --- XIAOZHI MULTI-SLOT LIVE RECORDING IMPLEMENTATION ---
async function toggleSlotRecording(slotIdx) {
    const btn = document.getElementById(`vpSlotBtn_${slotIdx}`);
    const statusEl = document.getElementById(`vpSlotStatus_${slotIdx}`);
    const audioEl = document.getElementById(`vpSlotAudio_${slotIdx}`);
    const clearBtn = document.getElementById(`vpSlotClear_${slotIdx}`);

    // If currently recording this slot, stop it
    if (vpActiveSlotIndex === slotIdx && vpSlotRecorders[slotIdx] && vpSlotRecorders[slotIdx].state === 'recording') {
        vpSlotRecorders[slotIdx].stop();
        return;
    }

    // If another slot is recording, stop it first
    if (vpActiveSlotIndex >= 0 && vpActiveSlotIndex !== slotIdx && vpSlotRecorders[vpActiveSlotIndex] && vpSlotRecorders[vpActiveSlotIndex].state === 'recording') {
        try { vpSlotRecorders[vpActiveSlotIndex].stop(); } catch(e){}
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        vpSlotChunks[slotIdx] = [];
        const recorder = new MediaRecorder(stream);
        vpSlotRecorders[slotIdx] = recorder;
        vpActiveSlotIndex = slotIdx;

        recorder.ondataavailable = e => {
            if (e.data.size > 0) vpSlotChunks[slotIdx].push(e.data);
        };

        recorder.onstop = () => {
            stream.getTracks().forEach(t => t.stop());
            vpActiveSlotIndex = -1;
            const blob = new Blob(vpSlotChunks[slotIdx], { type: recorder.mimeType || 'audio/webm' });
            vpSlots[slotIdx] = blob;

            if (audioEl) {
                audioEl.src = URL.createObjectURL(blob);
                audioEl.style.display = 'block';
            }
            if (clearBtn) clearBtn.style.display = 'inline-block';
            if (btn) {
                btn.innerHTML = '🔴 Thu Lại';
                btn.style.background = '#475569';
            }
            if (statusEl) {
                statusEl.innerHTML = `<span style="color: #34d399; font-weight: 700;">✅ Đã thu (${(blob.size / 1024).toFixed(1)} KB)</span>`;
            }
            updateSlotsRecordedSummary();
        };

        recorder.start();
        if (btn) {
            btn.innerHTML = '⏹️ Dừng Thu';
            btn.style.background = '#eab308';
        }
        if (statusEl) {
            statusEl.innerHTML = '<span style="color: #ef4444; animation: pulse 1s infinite;">● Đang thu... Nói 3-5s</span>';
        }
    } catch (err) {
        alert('Không thể mở micro: ' + err.message);
        if (statusEl) statusEl.textContent = 'Lỗi mic';
    }
}

function clearSlotAudio(slotIdx) {
    vpSlots[slotIdx] = null;
    const audioEl = document.getElementById(`vpSlotAudio_${slotIdx}`);
    const clearBtn = document.getElementById(`vpSlotClear_${slotIdx}`);
    const btn = document.getElementById(`vpSlotBtn_${slotIdx}`);
    const statusEl = document.getElementById(`vpSlotStatus_${slotIdx}`);

    if (audioEl) { audioEl.src = ''; audioEl.style.display = 'none'; }
    if (clearBtn) clearBtn.style.display = 'none';
    if (btn) {
        btn.innerHTML = '🔴 Thu Âm';
        btn.style.background = slotIdx === 0 ? '#ef4444' : (slotIdx === 1 ? '#0284c7' : '#7c3aed');
    }
    if (statusEl) statusEl.textContent = 'Chưa thu âm';
    updateSlotsRecordedSummary();
}

function updateSlotsRecordedSummary() {
    const recordedCount = vpSlots.filter(s => s !== null).length;
    const summaryEl = document.getElementById('vpSlotsRecordedSummary');
    const saveBtn = document.getElementById('vpBtnSaveMulti');

    if (summaryEl) summaryEl.textContent = `Đã thu: ${recordedCount}/3 mẫu`;
    if (saveBtn) {
        if (recordedCount >= 1) {
            saveBtn.disabled = false;
            saveBtn.style.opacity = '1';
            saveBtn.innerHTML = `💾 Huấn Luyện & Lưu (${recordedCount} Mẫu)`;
        } else {
            saveBtn.disabled = true;
            saveBtn.style.opacity = '0.5';
            saveBtn.innerHTML = '💾 Huấn Luyện & Lưu Vân Giọng (XiaoZhi)';
        }
    }
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
            const res = reader.result;
            const b64 = res.split(',')[1];
            resolve(b64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function saveMultiSlotVoiceprint() {
    const nameInput = document.getElementById('vpEnrollName');
    const name = nameInput ? nameInput.value.trim() : '';
    if (!name) {
        alert('Vui lòng nhập tên thành viên (ví dụ: Anh Tý, Mẹ, Bố...)');
        if (nameInput) nameInput.focus();
        return;
    }

    const validBlobs = vpSlots.filter(s => s !== null);
    if (validBlobs.length === 0) {
        alert('Bạn chưa thu mẫu giọng nào. Vui lòng thu ít nhất mẫu số 1.');
        return;
    }

    const saveBtn = document.getElementById('vpBtnSaveMulti');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '⏳ Đang tính toán Centroid Vector...';
    }

    try {
        const base64List = [];
        for (const blob of validBlobs) {
            const b64 = await blobToBase64(blob);
            base64List.push(b64);
        }

        const res = await fetch('/api/voiceprint/enroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                speaker_name: name,
                audio_list_base64: base64List
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert(`✅ Tuyệt vời! Đã huấn luyện hồ sơ vân giọng cho "${name}" thành công từ ${validBlobs.length} mẫu âm thanh (Thuật toán XiaoZhi Centroid).`);
            if (nameInput) nameInput.value = '';
            for (let i = 0; i < 3; i++) clearSlotAudio(i);
            switchVoiceprintTab('speakers');
            loadVoiceprintSpeakers();
        } else {
            alert(`❌ Lỗi tạo vân giọng: ${data.message || 'Không thể xử lý'}`);
        }
    } catch (err) {
        alert('Lỗi kết nối khi gửi mẫu giọng: ' + err.message);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            updateSlotsRecordedSummary();
        }
    }
}

// --- XIAOZHI HISTORY MULTI-SELECTION IMPLEMENTATION ---
async function loadHistoryForVoiceprint() {
    const container = document.getElementById('vpHistListContainer');
    const knownSelect = document.getElementById('vpHistKnownSpeakersSelect');
    if (!container) return;

    container.innerHTML = '<div style="padding: 30px; text-align: center; color: #94a3b8; font-size: 13px;">⏳ Đang tải các đoạn ghi âm từ lịch sử...</div>';

    // Populate known speakers select
    try {
        const spkRes = await fetch('/api/voiceprint/speakers');
        if (spkRes.ok) {
            const spkData = await spkRes.json();
            const speakers = spkData.speakers || [];
            if (knownSelect) {
                let sHtml = '<option value="">-- Có sẵn --</option>';
                speakers.forEach(s => {
                    sHtml += `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)}</option>`;
                });
                knownSelect.innerHTML = sHtml;
            }
        }
    } catch (e) {}

    try {
        const res = await fetch('/api/history?limit=100&type=voice_ai');
        if (!res.ok) {
            container.innerHTML = '<div style="padding: 24px; text-align: center; color: #f87171;">Không thể tải lịch sử.</div>';
            return;
        }
        const data = await res.json();
        const records = (data.records || []).filter(r => r.audio_file);
        vpHistoryRecordsForVoiceprint = records;

        if (records.length === 0) {
            container.innerHTML = `<div style="padding: 40px; text-align: center; color: #94a3b8;">
                <div style="font-size: 28px; margin-bottom: 8px;">📭</div>
                Chưa có file ghi âm giọng nói nào trong lịch sử.<br>
                <span style="font-size: 12px; color: #64748b;">Hãy nói chuyện với Nala qua ESP32 Panel hoặc dùng tab "Thu Trực Tiếp".</span>
            </div>`;
            return;
        }

        let html = `
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; text-align: left;">
                <thead>
                    <tr style="background: #182234; color: #94a3b8; border-bottom: 1px solid #334155; font-size: 12px;">
                        <th style="padding: 10px 14px; width: 40px; text-align: center;">
                            <input type="checkbox" id="vpHistCheckAll" onchange="toggleSelectAllHistoryVp(this.checked)" style="cursor: pointer;">
                        </th>
                        <th style="padding: 10px 14px; width: 140px;">Thời Gian</th>
                        <th style="padding: 10px 14px; width: 140px;">Phòng / Thiết Bị</th>
                        <th style="padding: 10px 14px;">Câu Nói (Văn Bản)</th>
                        <th style="padding: 10px 14px; width: 200px;">Ghi Âm &amp; Độ Dài</th>
                    </tr>
                </thead>
                <tbody>
        `;

        records.forEach(r => {
            html += `
                <tr style="border-bottom: 1px solid rgba(51, 65, 85, 0.5); transition: background 0.15s;" onmouseover="this.style.background='rgba(30, 41, 59, 0.5)'" onmouseout="this.style.background='transparent'">
                    <td style="padding: 10px 14px; text-align: center;">
                        <input type="checkbox" class="vp-hist-chk" value="${escapeHtml(r.audio_file)}" onchange="updateVpHistSelectedCount()" style="cursor: pointer; width: 16px; height: 16px;">
                    </td>
                    <td style="padding: 10px 14px; color: #94a3b8; font-size: 11px;">
                        ${escapeHtml(r.datetime || '')}
                    </td>
                    <td style="padding: 10px 14px; color: #cbd5e1; font-weight: 500;">
                        ${escapeHtml(r.room_name || r.device_code || 'Khách')}
                        ${r.speaker ? `<div style="font-size: 10px; color: #38bdf8;">Đã nhận: ${escapeHtml(r.speaker)}</div>` : ''}
                    </td>
                    <td style="padding: 10px 14px; color: #f1f5f9;">
                        "${escapeHtml(r.text || '')}"
                    </td>
                    <td style="padding: 10px 14px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <audio controls preload="none" style="height: 28px; width: 150px;">
                                <source src="/api/history/audio/${escapeHtml(r.audio_file)}" type="audio/wav">
                            </audio>
                            <span style="font-size: 11px; color: #94a3b8;">${r.duration || 0}s</span>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
        updateVpHistSelectedCount();

    } catch (e) {
        container.innerHTML = `<div style="padding: 24px; text-align: center; color: #f87171;">Lỗi tải lịch sử: ${e.message}</div>`;
    }
}

function toggleSelectAllHistoryVp(checked) {
    const chks = document.querySelectorAll('.vp-hist-chk');
    chks.forEach(c => { c.checked = checked; });
    updateVpHistSelectedCount();
}

function updateVpHistSelectedCount() {
    const chks = document.querySelectorAll('.vp-hist-chk:checked');
    const count = chks.length;
    const countEl = document.getElementById('vpHistSelectedCount');
    const btn = document.getElementById('vpHistBtnEnroll');
    const nameInput = document.getElementById('vpHistTargetName');
    const name = nameInput ? nameInput.value.trim() : '';

    if (countEl) countEl.textContent = count;
    if (btn) {
        if (count > 0 && name.length > 0) {
            btn.disabled = false;
            btn.style.opacity = '1';
            btn.innerHTML = `✨ Gộp & Huấn Luyện (${count} Mẫu)`;
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
            btn.innerHTML = '✨ Gộp & Huấn Luyện Vân Giọng';
        }
    }
}

async function enrollSelectedHistoryRecordings() {
    const nameInput = document.getElementById('vpHistTargetName');
    const name = nameInput ? nameInput.value.trim() : '';
    if (!name) {
        alert('Vui lòng nhập hoặc chọn tên thành viên (ví dụ: Anh Tý, Mẹ...)');
        if (nameInput) nameInput.focus();
        return;
    }

    const chks = document.querySelectorAll('.vp-hist-chk:checked');
    const filenames = Array.from(chks).map(c => c.value);
    if (filenames.length === 0) {
        alert('Vui lòng tick chọn ít nhất 1 (khuyên dùng 2-5) đoạn ghi âm của người này.');
        return;
    }

    const btn = document.getElementById('vpHistBtnEnroll');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `⏳ Đang gộp ${filenames.length} vector...`;
    }

    try {
        const res = await fetch('/api/voiceprint/enroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                speaker_name: name,
                filenames: filenames
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert(`✅ Thành công! Đã tạo và cập nhật vân giọng cho "${name}" bằng cách tính Centroid Vector từ ${filenames.length} mẫu âm thanh lịch sử.`);
            switchVoiceprintTab('speakers');
            loadVoiceprintSpeakers();
        } else {
            alert(`❌ Không thể tạo vân giọng: ${data.message || 'Lỗi xử lý'}`);
        }
    } catch (e) {
        alert('Lỗi kết nối: ' + e.message);
    } finally {
        if (btn) {
            btn.disabled = false;
            updateVpHistSelectedCount();
        }
    }
}
'''

# Insert new methods before async function toggleTestRecording
assert 'async function toggleTestRecording()' in html, "Could not find toggleTestRecording"
html = html.replace('async function toggleTestRecording()', new_methods + '\nasync function toggleTestRecording()', 1)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(html)

print("Successfully updated index.html to v3.0.6 with XiaoZhi Multi-Slot and History Voiceprint features!")
