import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Check open & close functions
required_funcs = [
    'openUserProfileMemoryModal', 'closeUserProfileMemoryModal', 'switchUserProfileMemoryTab',
    'openLivingContextAutomationModal', 'closeLivingContextAutomationModal', 'switchLivingContextTab',
    'openCommunicationModal', 'closeCommunicationModal', 'switchCommunicationTab',
    'openSystemSettingsModal', 'closeSystemSettingsModal', 'switchSystemSettingsTab'
]

print("=== CHECKING CORE MODAL FUNCTIONS ===")
for fn in required_funcs:
    found = f'function {fn}' in html
    print(f"{fn}: {'✅ OK' if found else '❌ MISSING'}")

# 2. Check each tab button and its target tab div
print("\n=== CHECKING TABS IN EACH MODAL ===")
tabs_map = {
    'userProfileMemoryModal': ['profile', 'vp', 'learned', 'context'],
    'livingContextAutomationModal': ['radar', 'rules'],
    'communicationModal': ['intercom', 'history'],
    'systemSettingsModal': ['role', 'ai', 'ha', 'ota']
}

for modal_id, tabs in tabs_map.items():
    print(f"\nModal: {modal_id}")
    for tab in tabs:
        # Check btn
        btn_candidates = [
            f'tab_{tab}_btn',
            f'tab_{modal_id[:3]}_{tab}_btn',
            f'tab_mem_{tab}_btn',
            f'tab_fsm_{tab}_btn',
            f'tab_comm_{tab}_btn',
            f'tab_sys_{tab}_btn'
        ]
        found_btn = [b for b in btn_candidates if f'id="{b}"' in html]
        
        # Check content div
        div_candidates = [
            f'tab_{tab}',
            f'tab_{modal_id[:3]}_{tab}',
            f'tab_mem_{tab}',
            f'tab_fsm_{tab}',
            f'tab_comm_{tab}',
            f'tab_sys_{tab}'
        ]
        found_div = [d for d in div_candidates if f'id="{d}"' in html]
        
        print(f"  Tab '{tab}': btn -> {found_btn or '❌ MISSING'}, div -> {found_div or '❌ MISSING'}")
