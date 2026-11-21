with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add var devices_db = {}; near top of script if not present
if 'var devices_db' not in content and 'let devices_db' not in content:
    idx_script = content.find('<script>')
    if idx_script != -1:
        insert_pos = content.find('\n', idx_script) + 1
        content = content[:insert_pos] + "    var devices_db = {};\n" + content[insert_pos:]
        print("✅ Added global var devices_db = {};")

# 2. Fix openAutomationEditorModal
old_editor_fn = '''function openAutomationEditorModal(ruleId = null) {
    const modal = document.getElementById('automationEditorModal');
    if (!modal) return;

    // Nạp danh sách phòng từ devices_db
    const roomSelect = document.getElementById('autoEditTargetRoom');
    if (roomSelect) {
        roomSelect.innerHTML = '<option value="all">🌐 Toàn Nhà (Mọi phòng)</option>';
        const seenRooms = new Set();
        for (const [code, dev] of Object.entries(devices_db || {})) {
            const rName = dev.room_name || `Phòng ${code}`;
            if (!seenRooms.has(rName)) {
                seenRooms.add(rName);
                const opt = document.createElement('option');
                opt.value = rName;
                opt.textContent = `📍 ${rName}`;
                roomSelect.appendChild(opt);
            }
        }
    }'''

new_editor_fn = '''function openAutomationEditorModal(ruleId = null) {
    const modal = document.getElementById('automationEditorModal');
    if (!modal) return;

    // Nạp danh sách phòng từ currentDevices / danh sách phòng hệ thống
    const roomSelect = document.getElementById('autoEditTargetRoom');
    if (roomSelect) {
        roomSelect.innerHTML = '<option value="all">🌐 Toàn Nhà (Mọi phòng)</option>';
        const seenRooms = new Set();

        const devList = (typeof currentDevices !== 'undefined' && Array.isArray(currentDevices)) ? currentDevices : [];
        for (const dev of devList) {
            const rName = dev.room_name || (dev.pairing_code ? `Phòng [${dev.pairing_code}]` : '');
            if (rName && !seenRooms.has(rName)) {
                seenRooms.add(rName);
                const opt = document.createElement('option');
                opt.value = rName;
                opt.textContent = `📍 ${rName}`;
                roomSelect.appendChild(opt);
            }
        }

        if (typeof devices_db !== 'undefined' && devices_db) {
            for (const [code, dev] of Object.entries(devices_db)) {
                const rName = dev.room_name || `Phòng ${code}`;
                if (rName && !seenRooms.has(rName)) {
                    seenRooms.add(rName);
                    const opt = document.createElement('option');
                    opt.value = rName;
                    opt.textContent = `📍 ${rName}`;
                    roomSelect.appendChild(opt);
                }
            }
        }

        if (seenRooms.size === 0) {
            ['Phòng ngủ ty', 'Phòng ngủ mẹ', 'Phòng khách', 'Bếp', 'Phòng làm việc'].forEach(rName => {
                const opt = document.createElement('option');
                opt.value = rName;
                opt.textContent = `📍 ${rName}`;
                roomSelect.appendChild(opt);
            });
        }
    }'''

assert old_editor_fn in content, "old_editor_fn target not found!"
content = content.replace(old_editor_fn, new_editor_fn, 1)
print("✅ Updated openAutomationEditorModal with safe room loading.")

# 3. Enhance loadAutomationRules with loading indicator
old_load_rules = '''async function loadAutomationRules() {
    const listEl = document.getElementById('vpAutomationRulesList');
    if (!listEl) return;
    try {
        const res = await fetch('/api/automations');'''

new_load_rules = '''async function loadAutomationRules() {
    const listEl = document.getElementById('vpAutomationRulesList');
    if (!listEl) return;
    listEl.innerHTML = '<div style="text-align: center; color: #94a3b8; font-size: 13px; padding: 24px;"><div style="font-size: 24px; margin-bottom: 8px;">⏳</div>Đang tải danh sách kịch bản...</div>';
    try {
        const res = await fetch('/api/automations');'''

assert old_load_rules in content, "old_load_rules target not found!"
content = content.replace(old_load_rules, new_load_rules, 1)
print("✅ Added loading indicator to loadAutomationRules.")

# 4. Enhance toggleRuleState with interactive feedback
old_toggle = '''async function toggleRuleState(ruleId) {
    try {
        const res = await fetch(`/api/automations/${ruleId}/toggle`, { method: 'POST' });
        if (res.ok) {
            loadAutomationRules();
        } else {
            alert('Không thể đổi trạng thái kịch bản');
        }
    } catch (e) {
        alert('Lỗi: ' + e.message);
    }
}'''

new_toggle = '''async function toggleRuleState(ruleId) {
    try {
        if (window.event && window.event.currentTarget) {
            const btn = window.event.currentTarget;
            btn.textContent = '⏳...';
            btn.style.opacity = '0.7';
        }
        const res = await fetch(`/api/automations/${ruleId}/toggle`, { method: 'POST' });
        if (res.ok) {
            await loadAutomationRules();
        } else {
            alert('Không thể đổi trạng thái kịch bản');
            await loadAutomationRules();
        }
    } catch (e) {
        alert('Lỗi: ' + e.message);
        await loadAutomationRules();
    }
}'''

assert old_toggle in content, "old_toggle target not found!"
content = content.replace(old_toggle, new_toggle, 1)
print("✅ Enhanced toggleRuleState.")

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("🎉 File index.html successfully updated!")
