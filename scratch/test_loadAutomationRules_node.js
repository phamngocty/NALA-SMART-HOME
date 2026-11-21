// Simulate browser environment in Node
const mockRules = [
    {
      "id": "rule_night_sleep_guard",
      "name": "Bảo vệ giấc ngủ sâu (Deep Sleep Guard)",
      "description": "Khi phòng ngủ ở trạng thái ngủ say, duy trì máy lạnh 26 độ êm dịu và triệt tiêu đèn trần",
      "enabled": false,
      "trigger": {
        "type": "living_context",
        "state": "deep_sleep"
      },
      "conditions": {
        "time_range": {
          "start": "22:30",
          "end": "06:30"
        },
        "max_lux": 15
      },
      "actions": [
        {
          "domain": "climate",
          "service": "set_temperature",
          "data": {
            "temperature": 26.0
          }
        }
      ]
    },
    {
      "id": "rule_night_path_light",
      "name": "Đèn dẫn đường thức giấc đêm (Night Path Light)",
      "description": "Khi thức giấc ban đêm, chỉ bật đèn ngủ hoặc đèn hắt dịu mắt 10%, không làm chói mắt",
      "enabled": false,
      "trigger": {
        "type": "living_context",
        "state": "night_wakeup"
      },
      "conditions": {
        "time_range": {
          "start": "00:00",
          "end": "05:45"
        },
        "max_lux": 15
      },
      "actions": [
        {
          "domain": "light",
          "service": "turn_on",
          "data": {
            "brightness_pct": 10
          }
        }
      ]
    },
    {
      "id": "rule_empty_room_powersave",
      "name": "Tiết kiệm điện khi rời phòng (Empty Room Eco)",
      "description": "Khi phòng vắng người liên tục, tự động tắt bớt đèn chiếu sáng",
      "enabled": false,
      "trigger": {
        "type": "living_context",
        "state": "empty"
      },
      "conditions": {
        "min_duration_sec": 300
      },
      "actions": [
        {
          "domain": "light",
          "service": "turn_off"
        }
      ]
    }
];

function escapeHtml(text) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return (text || '').replace(/[&<>"']/g, m => map[m]);
}

let listEl = { innerHTML: '' };
let currentLoadedRules = [];

function runLoadRules(rules) {
    currentLoadedRules = rules;

    const triggerLabels = {
        'deep_sleep': '💤 Ngủ sâu',
        'night_wakeup': '🌙 Thức giấc đêm',
        'empty': '⚪ Phòng vắng',
        'active': '🟢 Có người',
        'approaching': '🚶 Lại gần'
    };

    let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
    for (const rule of rules) {
        const ruleId = rule.id || rule.rule_id;
        const isEnabled = !!rule.enabled;
        const toggleBg = isEnabled ? '#10b981' : '#475569';
        const toggleText = isEnabled ? 'ĐANG BẬT' : 'ĐÃ TẮT';

        const trig = rule.trigger || {};
        const trigLabel = triggerLabels[trig.state] || trig.state || 'Ngữ cảnh';

        const conds = rule.conditions || {};
        const condPills = [];
        if (conds.target_room && conds.target_room !== 'all') condPills.push(`📍 ${escapeHtml(conds.target_room)}`);
        if (conds.time_range) condPills.push(`⏰ ${conds.time_range.start} - ${conds.time_range.end}`);
        if (conds.max_lux !== undefined) condPills.push(`🌑 Lux ≤ ${conds.max_lux}`);
        if (conds.occupant) condPills.push(`👤 ${escapeHtml(conds.occupant)}`);

        const actionPills = [];
        for (const act of (rule.actions || [])) {
            if (act.domain === 'climate') {
                if (act.service === 'set_temperature') actionPills.push(`❄️ Điều hòa ${act.data?.temperature || 26}°C`);
                else if (act.service === 'turn_off') actionPills.push(`⭕ Tắt điều hòa`);
            } else if (act.domain === 'light') {
                if (act.service === 'turn_off') actionPills.push(`⭕ Tắt đèn`);
                else if (act.service === 'turn_on') {
                    const br = act.data?.brightness_pct;
                    actionPills.push(`💡 Bật đèn ${br ? br + '%' : ''}`);
                }
            }
        }

        html += `<div style="background: #1e293b; border: 1px solid ${isEnabled ? 'rgba(16, 185, 129, 0.4)' : '#334155'}; border-radius: 12px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 14px;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
                        <span style="font-weight: 700; color: #f8fafc; font-size: 14px;">${escapeHtml(rule.name || ruleId)}</span>
                        <span style="font-size: 11px; background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 8px; border-radius: 6px; font-weight: 600;">${trigLabel}</span>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">${escapeHtml(rule.description || '')}</div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button type="button" onclick="toggleRuleState('${ruleId}')" style="background: ${toggleBg}; color: white; border: none; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 11px; cursor: pointer; transition: all 0.2s;">
                        ${toggleText}
                    </button>
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #334155; padding-top: 10px; font-size: 11px; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; gap: 6px; flex-wrap: wrap; align-items: center;">
                    <span style="color: #64748b;">Ràng buộc:</span>
                    ${condPills.length > 0 ? condPills.map(p => `<span style="background: #0f172a; padding: 2px 7px; border-radius: 4px; color: #cbd5e1;">${p}</span>`).join('') : '<span style="color: #94a3b8;">Không giới hạn</span>'}
                    <span style="color: #64748b; margin-left: 6px;">Hành động:</span>
                    ${actionPills.length > 0 ? actionPills.map(p => `<span style="background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 2px 7px; border-radius: 4px; font-weight: 600;">${p}</span>`).join('') : '<span style="color: #94a3b8;">Chưa gán</span>'}
                </div>
                <div style="display: flex; gap: 8px;">
                    <button type="button" onclick="editAutomationRule('${ruleId}')" style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.35); color: #38bdf8; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
                        ✏️ Sửa
                    </button>
                    <button type="button" onclick="deleteAutomationRule('${ruleId}')" style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.35); color: #f87171; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: 700; cursor: pointer;">
                        🗑️ Xóa
                    </button>
                </div>
            </div>
        </div>`;
    }
    html += '</div>';
    listEl.innerHTML = html;
    console.log("HTML successfully rendered! Length:", html.length);
}

runLoadRules(mockRules);
