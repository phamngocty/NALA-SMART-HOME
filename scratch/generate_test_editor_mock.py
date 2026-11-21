with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('function openAutomationEditorModal')
idx_end = text.find('function closeAutomationEditorModal', idx)
fn_code = text[idx:idx_end]

# Run it in simulated DOM environment
test_runner = f"""
{fn_code}

let currentDevices = [
    {{ pairing_code: '881C', room_name: 'Phòng ngủ ty', online: true }},
    {{ pairing_code: 'D6F4', room_name: 'Phòng ngủ mẹ', online: false }}
];

let currentLoadedRules = [
    {{ id: 'rule_1', name: 'Rule 1', enabled: true }}
];

let docMock = {{
    autoEditTargetRoom: {{ innerHTML: '', appendChild: (c) => {{}} }},
    automationEditorModal: {{ style: {{ display: '' }}, classList: {{ add: () => {{}} }} }},
    autoEditRuleId: {{ value: '' }},
    autoEditorBadge: {{ textContent: '' }},
    autoEditName: {{ value: '' }},
    autoEditDesc: {{ value: '' }},
    autoEditTriggerState: {{ value: '' }},
    autoEditTimeStart: {{ value: '' }},
    autoEditTimeEnd: {{ value: '' }},
    autoEditMaxLux: {{ value: '' }},
    autoEditClimateAction: {{ value: '' }},
    autoEditClimateTemp: {{ value: '' }},
    autoEditLightAction: {{ value: '' }},
    autoEditEnabled: {{ checked: false }},
    autoBtnDelete: {{ style: {{ display: '' }} }}
}};

global.document = {{
    getElementById: (id) => docMock[id] || null
}};

global.toggleClimateTempInput = () => {{}};

try {{
    console.log("Testing openAutomationEditorModal(null)...");
    openAutomationEditorModal(null);
    console.log("✅ Success! Modal display:", docMock.automationEditorModal.style.display);

    console.log("Testing openAutomationEditorModal('rule_1')...");
    openAutomationEditorModal('rule_1');
    console.log("✅ Success! Editing ruleId:", docMock.autoEditRuleId.value);
}} catch (e) {{
    console.error("❌ ERROR:", e);
    process.exit(1);
}}
"""

with open('scratch/test_editor_mock.js', 'w', encoding='utf-8') as f:
    f.write(test_runner)
