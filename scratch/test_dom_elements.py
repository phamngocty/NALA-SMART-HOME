with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re

tests = [
    {
        "modal": "userProfileMemoryModal",
        "switch_fn": "switchUserProfileMemoryTab",
        "tabs": ['members', 'voiceprint', 'memory', 'test'],
        "prefix": "tab_upm_"
    },
    {
        "modal": "livingContextAutomationModal",
        "switch_fn": "switchLivingContextTab",
        "tabs": ['fsm', 'rules'],
        "prefix": "tab_lc_"
    },
    {
        "modal": "communicationModal",
        "switch_fn": "switchCommunicationTab",
        "tabs": ['intercom', 'history'],
        "prefix": "tab_comm_"
    },
    {
        "modal": "systemSettingsModal",
        "switch_fn": "switchSystemSettingsTab",
        "tabs": ['role', 'ai', 'ext', 'ha', 'ota'],
        "prefix": "tab_sys_"
    }
]

print("=== CHECKING ALL DOM ELEMENTS FOR ALL TABS ===")
for test in tests:
    print(f"\nModal: {test['modal']} (Prefix: {test['prefix']})")
    for t in test['tabs']:
        btn_id = f"{test['prefix']}{t}_btn"
        content_id = f"{test['prefix']}{t}"
        
        has_btn = f'id="{btn_id}"' in html
        has_content = f'id="{content_id}"' in html
        
        status = "✅ OK" if (has_btn and has_content) else "❌ MISMATCH"
        print(f"  [{status}] Tab '{t}': btn('{btn_id}')={has_btn}, content('{content_id}')={has_content}")
