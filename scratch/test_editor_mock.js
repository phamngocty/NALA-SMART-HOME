
function openAutomationEditorModal(ruleId = null) {
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
    }

    if (ruleId) {
        // Chế độ Chỉnh Sửa
        const rule = currentLoadedRules.find(r => (r.id || r.rule_id) === ruleId);
        if (!rule) return;
        document.getElementById('autoEditRuleId').value = ruleId;
        document.getElementById('autoEditorBadge').textContent = 'Chỉnh Sửa';
        document.getElementById('autoEditName').value = rule.name || '';
        document.getElementById('autoEditDesc').value = rule.description || '';
        document.getElementById('autoEditTriggerState').value = rule.trigger?.state || 'deep_sleep';
        document.getElementById('autoEditTargetRoom').value = rule.conditions?.target_room || 'all';
        document.getElementById('autoEditTimeStart').value = rule.conditions?.time_range?.start || '';
        document.getElementById('autoEditTimeEnd').value = rule.conditions?.time_range?.end || '';
        document.getElementById('autoEditMaxLux').value = rule.conditions?.max_lux !== undefined ? rule.conditions.max_lux : '';
        document.getElementById('autoEditEnabled').checked = rule.enabled !== false;

        let climAct = 'none';
        let climTemp = 26;
        let lightAct = 'none';
        for (const act of (rule.actions || [])) {
            if (act.domain === 'climate') {
                if (act.service === 'set_temperature') {
                    climAct = 'set_temp';
                    climTemp = act.data?.temperature || 26;
                } else if (act.service === 'turn_off') {
                    climAct = 'turn_off';
                }
            } else if (act.domain === 'light') {
                if (act.service === 'turn_off') lightAct = 'turn_off';
                else if (act.service === 'turn_on') {
                    const br = act.data?.brightness_pct;
                    if (br === 10) lightAct = 'dim_10';
                    else if (br === 30) lightAct = 'dim_30';
                    else if (br === 50) lightAct = 'dim_50';
                    else lightAct = 'turn_on_100';
                }
            }
        }
        document.getElementById('autoEditClimateAction').value = climAct;
        document.getElementById('autoEditClimateTemp').value = climTemp;
        document.getElementById('autoEditLightAction').value = lightAct;
        toggleClimateTempInput();

        document.getElementById('autoBtnDelete').style.display = 'inline-block';
    } else {
        // Chế độ Tạo Mới
        document.getElementById('autoEditRuleId').value = '';
        document.getElementById('autoEditorBadge').textContent = 'Tạo Mới';
        document.getElementById('autoEditName').value = '';
        document.getElementById('autoEditDesc').value = '';
        document.getElementById('autoEditTriggerState').value = 'deep_sleep';
        document.getElementById('autoEditTargetRoom').value = 'all';
        document.getElementById('autoEditTimeStart').value = '';
        document.getElementById('autoEditTimeEnd').value = '';
        document.getElementById('autoEditMaxLux').value = '';
        document.getElementById('autoEditClimateAction').value = 'none';
        document.getElementById('autoEditClimateTemp').value = '26';
        document.getElementById('autoEditLightAction').value = 'none';
        document.getElementById('autoEditEnabled').checked = true;
        toggleClimateTempInput();

        document.getElementById('autoBtnDelete').style.display = 'none';
    }

    modal.style.display = 'flex';
    modal.classList.add('active');
}



let currentDevices = [
    { pairing_code: '881C', room_name: 'Phòng ngủ ty', online: true },
    { pairing_code: 'D6F4', room_name: 'Phòng ngủ mẹ', online: false }
];

let currentLoadedRules = [
    { id: 'rule_1', name: 'Rule 1', enabled: true }
];

let docMock = {
    autoEditTargetRoom: { innerHTML: '', appendChild: (c) => {} },
    automationEditorModal: { style: { display: '' }, classList: { add: () => {} } },
    autoEditRuleId: { value: '' },
    autoEditorBadge: { textContent: '' },
    autoEditName: { value: '' },
    autoEditDesc: { value: '' },
    autoEditTriggerState: { value: '' },
    autoEditTimeStart: { value: '' },
    autoEditTimeEnd: { value: '' },
    autoEditMaxLux: { value: '' },
    autoEditClimateAction: { value: '' },
    autoEditClimateTemp: { value: '' },
    autoEditLightAction: { value: '' },
    autoEditEnabled: { checked: false },
    autoBtnDelete: { style: { display: '' } }
};

global.document = {
    getElementById: (id) => docMock[id] || null
};

global.toggleClimateTempInput = () => {};

try {
    console.log("Testing openAutomationEditorModal(null)...");
    openAutomationEditorModal(null);
    console.log("✅ Success! Modal display:", docMock.automationEditorModal.style.display);

    console.log("Testing openAutomationEditorModal('rule_1')...");
    openAutomationEditorModal('rule_1');
    console.log("✅ Success! Editing ruleId:", docMock.autoEditRuleId.value);
} catch (e) {
    console.error("❌ ERROR:", e);
    process.exit(1);
}
