import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Fix display: none on tab_vp_enroll and tab_vp_history
old_live_wrapper = """<div id="sub_vp_live_panel" style="display: block;">
                        <div id="tab_vp_enroll" style="display: none;">"""

new_live_wrapper = """<div id="sub_vp_live_panel" style="display: block;">
                        <div id="tab_vp_enroll" style="display: block;">"""

assert old_live_wrapper in html, "old_live_wrapper not found"
html = html.replace(old_live_wrapper, new_live_wrapper, 1)

old_hist_wrapper = """<div id="sub_vp_hist_panel" style="display: none;">
                        <div id="tab_vp_history" style="display: none;">"""

new_hist_wrapper = """<div id="sub_vp_hist_panel" style="display: none;">
                        <div id="tab_vp_history" style="display: block;">"""

assert old_hist_wrapper in html, "old_hist_wrapper not found"
html = html.replace(old_hist_wrapper, new_hist_wrapper, 1)

# 2. Add description input in Live Enroll form
old_enroll_name_block = """                        <div style="margin-bottom: 18px;">
                            <label style="display: block; font-size: 13px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Tên thành viên / Người nói:</label>
                            <input type="text" id="vpEnrollName" placeholder="Ví dụ: Anh Tý, Mẹ, Bố, Linh..." style="width: 100%; box-sizing: border-box; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px;">
                        </div>"""

new_enroll_name_block = """                        <div style="margin-bottom: 14px;">
                            <label style="display: block; font-size: 13px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Tên thành viên / Người nói:</label>
                            <input type="text" id="vpEnrollName" placeholder="Ví dụ: Anh Tý, Mẹ, Bố, Linh..." style="width: 100%; box-sizing: border-box; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 14px;">
                        </div>
                        <div style="margin-bottom: 18px;">
                            <label style="display: block; font-size: 13px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">Mô tả vai trò / Xưng hô:</label>
                            <input type="text" id="vpEnrollDesc" placeholder="Ví dụ: Chủ nhà, quyền Admin, Mẹ, Con nhỏ, Khách..." style="width: 100%; box-sizing: border-box; background: #1e293b; border: 1px solid #475569; color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 13px;">
                        </div>"""

assert old_enroll_name_block in html, "old_enroll_name_block not found"
html = html.replace(old_enroll_name_block, new_enroll_name_block, 1)

# 3. Add description input in History Enroll form
old_hist_bar = """                            <!-- ACTION BAR: CHỌN TÊN VÀ NÚT HUẤN LUYỆN -->
                            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 250px;">
                                    <label style="font-size: 13px; font-weight: 700; color: #f8fafc; white-space: nowrap;">Tên thành viên:</label>
                                    <input type="text" id="vpHistTargetName" oninput="updateVpHistSelectedCount()" placeholder="Gõ tên hoặc chọn bên phải..." style="flex: 1; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 13px;">
                                    <select id="vpHistKnownSpeakersSelect" onchange="if(this.value) { document.getElementById('vpHistTargetName').value = this.value; updateVpHistSelectedCount(); }" style="background: #0f172a; border: 1px solid #475569; color: #94a3b8; padding: 8px 10px; border-radius: 6px; font-size: 12px; max-width: 140px;">
                                        <option value="">-- Có sẵn --</option>
                                    </select>
                                </div>"""

new_hist_bar = """                            <!-- ACTION BAR: CHỌN TÊN VÀ NÚT HUẤN LUYỆN -->
                            <div style="background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 16px; display: flex; align-items: center; justify-content: space-between; gap: 14px; flex-wrap: wrap;">
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 250px;">
                                    <label style="font-size: 13px; font-weight: 700; color: #f8fafc; white-space: nowrap;">Tên thành viên:</label>
                                    <input type="text" id="vpHistTargetName" oninput="updateVpHistSelectedCount()" placeholder="Gõ tên hoặc chọn bên phải..." style="flex: 1; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 13px;">
                                    <select id="vpHistKnownSpeakersSelect" onchange="if(this.value) { document.getElementById('vpHistTargetName').value = this.value; updateVpHistSelectedCount(); }" style="background: #0f172a; border: 1px solid #475569; color: #94a3b8; padding: 8px 10px; border-radius: 6px; font-size: 12px; max-width: 140px;">
                                        <option value="">-- Có sẵn --</option>
                                    </select>
                                </div>
                                <div style="display: flex; align-items: center; gap: 10px; flex: 1; min-width: 220px;">
                                    <label style="font-size: 13px; font-weight: 700; color: #cbd5e1; white-space: nowrap;">Mô tả vai trò:</label>
                                    <input type="text" id="vpHistDesc" placeholder="Ví dụ: Chủ nhà, quyền Admin, Mẹ..." style="flex: 1; background: #0f172a; border: 1px solid #475569; color: #fff; padding: 8px 12px; border-radius: 6px; font-size: 13px;">
                                </div>"""

assert old_hist_bar in html, "old_hist_bar not found"
html = html.replace(old_hist_bar, new_hist_bar, 1)

# 4. Update saveMultiSlotVoiceprint
idx_save_multi = html.find('async function saveMultiSlotVoiceprint() {')
assert idx_save_multi != -1, "saveMultiSlotVoiceprint not found"
idx_save_multi_end = html.find('// --- XIAOZHI HISTORY MULTI-SELECTION IMPLEMENTATION ---', idx_save_multi)
assert idx_save_multi_end != -1, "saveMultiSlotVoiceprint end not found"

new_save_multi_func = """async function saveMultiSlotVoiceprint() {
    const nameInput = document.getElementById('vpEnrollName');
    const descInput = document.getElementById('vpEnrollDesc');
    const name = nameInput ? nameInput.value.trim() : '';
    const desc = descInput ? descInput.value.trim() : '';
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
                description: desc,
                audio_list_base64: base64List
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert(`✅ Tuyệt vời! Đã huấn luyện hồ sơ vân giọng cho "${name}" thành công từ ${validBlobs.length} mẫu âm thanh (Thuật toán XiaoZhi Centroid).`);
            if (nameInput) nameInput.value = '';
            if (descInput) descInput.value = '';
            for (let i = 0; i < 3; i++) clearSlotAudio(i);
            switchUserProfileMemoryTab('members');
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

"""
html = html[:idx_save_multi] + new_save_multi_func + html[idx_save_multi_end:]

# 5. Update enrollSelectedHistoryRecordings (make it async and handle description)
idx_hist_enroll = html.find('function enrollSelectedHistoryRecordings() {')
assert idx_hist_enroll != -1, "enrollSelectedHistoryRecordings not found"
idx_hist_enroll_end = html.find('async function toggleTestRecording()', idx_hist_enroll)
assert idx_hist_enroll_end != -1, "toggleTestRecording not found"

new_hist_enroll_func = """async function enrollSelectedHistoryRecordings() {
    const nameInput = document.getElementById('vpHistTargetName');
    const descInput = document.getElementById('vpHistDesc');
    const name = nameInput ? nameInput.value.trim() : '';
    const desc = descInput ? descInput.value.trim() : '';
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
                description: desc,
                filenames: filenames
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            alert(`✅ Thành công! Đã tạo và cập nhật vân giọng cho "${name}" bằng cách tính Centroid Vector từ ${filenames.length} mẫu âm thanh lịch sử.`);
            if (nameInput) nameInput.value = '';
            if (descInput) descInput.value = '';
            switchUserProfileMemoryTab('members');
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

function prepareTrainMore(name, desc = '') {
    switchUserProfileMemoryTab('voiceprint');
    if (typeof switchVoiceprintSubMode === 'function') switchVoiceprintSubMode('live');
    const nameInput = document.getElementById('vpEnrollName');
    const descInput = document.getElementById('vpEnrollDesc');
    const histNameInput = document.getElementById('vpHistTargetName');
    const histDescInput = document.getElementById('vpHistDesc');

    if (nameInput) nameInput.value = name;
    if (descInput) descInput.value = desc;
    if (histNameInput) histNameInput.value = name;
    if (histDescInput) histDescInput.value = desc;
}

"""
html = html[:idx_hist_enroll] + new_hist_enroll_func + html[idx_hist_enroll_end:]

# 6. Update loadVoiceprintSpeakers card rendering
old_card_render = """        let html = '';
        for (const spk of speakers) {
            html += `<div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #06b6d4, #3b82f6); display: flex; align-items: center; justify-content: center; font-size: 20px; color: white; font-weight: 700; box-shadow: 0 4px 10px rgba(6, 182, 212, 0.3);">
                        ${escapeHtml(spk.name.charAt(0).toUpperCase())}
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 15px; color: #f8fafc;">${escapeHtml(spk.name)}</div>
                        <div style="font-size: 11px; color: #38bdf8; display: flex; align-items: center; gap: 4px; margin-top: 2px;">
                            <span>●</span> ${spk.samples_count || 1} mẫu vector • ${(spk.duration_sec || 0).toFixed(1)}s
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #334155; padding-top: 10px; font-size: 11px; color: #94a3b8;">
                    <span>Cập nhật: ${spk.last_updated ? new Date(spk.last_updated * 1000).toLocaleDateString('vi-VN') : 'Mới'}</span>
                    <button type="button" onclick="deleteVoiceprintSpeaker('${escapeHtml(spk.name)}')" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
                        🗑️ Xóa
                    </button>
                </div>
            </div>`;
        }"""

new_card_render = """        let html = '';
        for (const spk of speakers) {
            const descBadge = spk.description 
                ? `<div style="font-size: 11px; color: #a78bfa; background: rgba(139, 92, 246, 0.15); border: 1px solid rgba(139, 92, 246, 0.3); padding: 2px 8px; border-radius: 4px; display: inline-block; margin-top: 4px;">🏷️ ${escapeHtml(spk.description)}</div>`
                : '';
            html += `<div style="background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
                <div style="display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px;">
                    <div style="width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #06b6d4, #3b82f6); display: flex; align-items: center; justify-content: center; font-size: 20px; color: white; font-weight: 700; box-shadow: 0 4px 10px rgba(6, 182, 212, 0.3); flex-shrink: 0;">
                        ${escapeHtml(spk.name.charAt(0).toUpperCase())}
                    </div>
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-weight: 700; font-size: 15px; color: #f8fafc; text-overflow: ellipsis; overflow: hidden; white-space: nowrap;">${escapeHtml(spk.name)}</div>
                        ${descBadge}
                        <div style="font-size: 11px; color: #38bdf8; display: flex; align-items: center; gap: 4px; margin-top: 4px;">
                            <span>●</span> ${spk.samples_count || 1} mẫu âm thanh Centroid
                        </div>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #334155; padding-top: 10px; font-size: 11px; color: #94a3b8; flex-wrap: wrap; gap: 6px;">
                    <span>${spk.last_updated ? new Date(spk.last_updated * 1000).toLocaleDateString('vi-VN') : 'Mới'}</span>
                    <div style="display: flex; gap: 6px;">
                        <button type="button" onclick="prepareTrainMore('${escapeHtml(spk.name)}', '${escapeHtml(spk.description || '')}')" style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); color: #38bdf8; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
                            🎙️ Thêm mẫu
                        </button>
                        <button type="button" onclick="deleteVoiceprintSpeaker('${escapeHtml(spk.name)}')" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #f87171; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
                            🗑️ Xóa
                        </button>
                    </div>
                </div>
            </div>`;
        }"""

assert old_card_render in html, "old_card_render not found"
html = html.replace(old_card_render, new_card_render, 1)

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("✅ Successfully patched index.html for Voiceprint & Memory enhancement!")
