import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Collect all element IDs present in HTML
all_ids = set(re.findall(r'id=["\']([a-zA-Z0-9_\-]+)["\']', html))
print(f"Total element IDs in index.html: {len(all_ids)}")

# Test 1: User Profile & Memory Modal tabs
print("\n--- Modal 1: userProfileMemoryModal ---")
upm_tabs = ['members', 'voiceprint', 'memory', 'test']
for t in upm_tabs:
    btn_id = f"tab_upm_{t}_btn"
    content_id = f"tab_upm_{t}"
    print(f"Tab '{t}': btn exists = {btn_id in all_ids}, content exists = {content_id in all_ids}")

# Check inner divs of upm_tabs
for t in upm_tabs:
    cid = f"tab_upm_{t}"
    idx = html.find(f'id="{cid}"')
    if idx != -1:
        chunk = html[idx:idx+2000]
        # check style of this div
        tag_match = re.search(r'<div[^>]*id=["\']' + cid + r'["\'][^>]*>', chunk)
        if tag_match:
            print(f"  Container {cid} tag: {tag_match.group(0)}")
        # check if immediate child has display:none
        inner_none = re.findall(r'<div[^>]*id=["\']([^"\']+)["\'][^>]*style=["\'][^"\']*display:\s*none[^"\']*["\']', chunk)
        if inner_none:
            print(f"  WARNING: Inner div with display:none inside {cid}: {inner_none}")

# Test 2: Living Context Modal tabs
print("\n--- Modal 2: livingContextAutomationModal ---")
lc_tabs = ['fsm', 'rules']
for t in lc_tabs:
    btn_id = f"tab_lc_{t}_btn"
    content_id = f"tab_lc_{t}"
    print(f"Tab '{t}': btn exists = {btn_id in all_ids}, content exists = {content_id in all_ids}")

# Test 3: Communication Modal tabs
print("\n--- Modal 3: communicationModal ---")
comm_tabs = ['intercom', 'history']
for t in comm_tabs:
    btn_id = f"tab_comm_{t}_btn"
    content_id = f"tab_comm_{t}"
    print(f"Tab '{t}': btn exists = {btn_id in all_ids}, content exists = {content_id in all_ids}")

# Test 4: System Settings Modal tabs
print("\n--- Modal 4: systemSettingsModal ---")
sys_tabs = ['role', 'ai', 'ext', 'ha', 'ota']
for t in sys_tabs:
    btn_id = f"tab_sys_{t}_btn"
    content_id = f"tab_sys_{t}"
    print(f"Tab '{t}': btn exists = {btn_id in all_ids}, content exists = {content_id in all_ids}")

# Check any function called in switch tabs:
# switchUserProfileMemoryTab calls:
#   loadVoiceprintSpeakers
#   loadHistoryForVoiceprint
#   loadMemoryData
# switchLivingContextTab calls:
#   loadLivingContextDashboard
#   loadAutomationRules
# switchCommunicationTab calls:
#   renderIntercomTargets
#   attachPttEvents
#   updateActiveIntercomCallsBanner
#   loadHistorySettings
#   loadHistoryModalData
# switchSystemSettingsTab calls:
#   loadXiaoZhiVoiceRole
#   loadAIConfigData
#   loadExtensionData
#   loadHAConfigData
#   loadOTAData

funcs_to_check = [
    'loadVoiceprintSpeakers',
    'loadHistoryForVoiceprint',
    'loadMemoryData',
    'loadLivingContextDashboard',
    'loadAutomationRules',
    'renderIntercomTargets',
    'attachPttEvents',
    'updateActiveIntercomCallsBanner',
    'loadHistorySettings',
    'loadHistoryModalData',
    'loadXiaoZhiVoiceRole',
    'loadAIConfigData',
    'loadExtensionData',
    'loadHAConfigData',
    'loadOTAData'
]

print("\n--- Checking functions invoked on tab switches ---")
for fn in funcs_to_check:
    has_fn = re.search(rf'function\s+{fn}\s*\(', html) is not None
    has_async_fn = re.search(rf'async\s+function\s+{fn}\s*\(', html) is not None
    print(f"Function {fn}: {'EXISTS' if (has_fn or has_async_fn) else 'MISSING!'}")
