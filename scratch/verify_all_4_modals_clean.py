import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

modals_and_tabs = {
    'userProfileMemoryModal': ['members', 'voiceprint', 'memory', 'test'],
    'livingContextAutomationModal': ['fsm', 'rules'],
    'communicationModal': ['intercom', 'history'],
    'systemSettingsModal': ['role', 'ai', 'ha', 'ota']
}

print("=== 1. MODAL & TAB CHECK ===")
for modal_id, tabs in modals_and_tabs.items():
    modal_exists = f'id="{modal_id}"' in html
    print(f"\nModal {modal_id}: {'✅ OK' if modal_exists else '❌ MISSING'}")
    prefix = {
        'userProfileMemoryModal': 'upm',
        'livingContextAutomationModal': 'lc',
        'communicationModal': 'comm',
        'systemSettingsModal': 'sys'
    }[modal_id]
    
    for t in tabs:
        btn_id = f'tab_{prefix}_{t}_btn'
        div_id = f'tab_{prefix}_{t}'
        has_btn = f'id="{btn_id}"' in html
        has_div = f'id="{div_id}"' in html
        print(f"  Tab '{t}': btn ({btn_id})={'✅' if has_btn else '❌'}, div ({div_id})={'✅' if has_div else '❌'}")

print("\n=== 2. ESSENTIAL DOM ELEMENTS CHECK ===")
essential_elements = [
    # 1. userProfileMemoryModal
    ('vpSpeakersGrid', 'Voiceprint Speakers Grid'),
    ('sub_vp_live_panel', 'Live 3-Slot Recording Panel'),
    ('sub_vp_hist_panel', 'History Multi-select Panel'),
    ('vpHistListContainer', 'Voice History List Container'),
    ('chkMemoryEnabled', 'Adaptive Memory Enable Checkbox'),
    
    # 2. livingContextAutomationModal
    ('vpContextRoomsGrid', 'FSM Radar Living Context Grid'),
    ('vpAutomationRulesList', 'Rule Engine Automation List'),
    
    # 3. communicationModal
    ('activeIntercomCallsContainer', 'Active Calls Alert Banner'),
    ('btnToggleWebSpeaker', 'Web Admin Speaker Toggle'),
    ('intercomTargetsGrid', 'Intercom Channel Targets Grid'),
    ('btnWebPtt', 'Push-to-Talk Button'),
    ('selHistoryRetention', 'History Auto-delete Retention Dropdown'),
    ('historyTableContainer', 'History Records Table Container'),
    ('historyListContent', 'History List Content Container'),
    
    # 4. systemSettingsModal
    ('xzVoiceDropdownContainer', 'XiaoZhi Voice Custom Dropdown'),
    ('xzRolePersona', 'XiaoZhi Voice Persona Prompt Textarea'),
    ('xzSpeakingRate', 'Speech Rate Slider'),
    ('xzSpeakingPitch', 'Speech Pitch Slider'),
    ('xzVadSpeed', 'VAD Recognition Speed Slider'),
    ('cfgGeminiKey', 'Gemini API Key Input'),
    ('haWsUrlInput', 'Home Assistant WebSocket URL Input'),
    ('haTokenInput', 'Home Assistant Token Input'),
    ('otaFileInput', 'OTA Firmware File Input'),
    ('otaTrackerList', 'Live OTA Progress Tracker List')
]

for el_id, desc in essential_elements:
    exists = f'id="{el_id}"' in html
    print(f"[{'✅ OK' if exists else '❌ MISSING'}] {desc} (id=\"{el_id}\")")
