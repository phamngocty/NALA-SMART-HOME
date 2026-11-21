import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all modal divs and their tabs
modals = [
    'userProfileMemoryModal',
    'livingContextAutomationModal',
    'communicationModal',
    'systemSettingsModal'
]

print("=== CHECKING TABS IN THE 4 MAIN MODALS ===")
for modal_id in modals:
    m = re.search(rf'<div[^>]*id=["\']{modal_id}["\'][^>]*>(.*?)<!-- END {modal_id}', content, re.DOTALL | re.IGNORECASE)
    if not m:
        # try without end comment
        idx = content.find(f'id="{modal_id}"')
        if idx != -1:
            snippet = content[idx:idx+25000]
            print(f"\n--- Found modal: {modal_id} ---")
            # find all tab_ ids
            tab_ids = re.findall(r'id=["\'](tab_[a-zA-Z0-9_]+)["\']', snippet)
            print(f"Tab IDs found: {tab_ids}")
            # check any inner display: none inside tabs
            for tid in tab_ids:
                # check tab block
                t_idx = snippet.find(f'id="{tid}"')
                if t_idx != -1:
                    t_chunk = snippet[t_idx:t_idx+1500]
                    # check if it has nested display: none in child divs
                    child_none = re.findall(r'(<div[^>]*id=["\']([^"\']+)["\'][^>]*style=["\'][^"\']*display:\s*none[^"\']*["\'][^>]*>)', t_chunk)
                    if child_none:
                        print(f"  [POTENTIAL BUG] Nested display:none in tab '{tid}': {child_none}")
    else:
        print(f"Modal {modal_id} parsed.")
