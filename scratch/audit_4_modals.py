import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Extract the 4 modals
modals = [
    'userProfileMemoryModal',
    'livingContextAutomationModal',
    'communicationModal',
    'systemSettingsModal'
]

print("=== CHECKING MODAL EXISTENCE ===")
for m in modals:
    idx = html.find(f'id="{m}"')
    print(f"Modal {m}: {'FOUND' if idx != -1 else 'MISSING'} at char {idx}")

# 2. Extract all onclick handlers in each modal
for m in modals:
    start = html.find(f'id="{m}"')
    if start == -1:
        continue
    # find next modal or end
    end = html.find('class="modal-overlay"', start + 1)
    if end == -1:
        end = html.find('</main>', start)
    modal_content = html[start:end]

    print(f"\n--- Checking functions & elements inside {m} ---")
    
    # find all onclick
    onclicks = re.findall(r'onclick=["\']([^"\']+)["\']', modal_content)
    for oc in set(onclicks):
        # get function name
        fn_match = re.match(r'([a-zA-Z0-9_]+)\(', oc.strip())
        if fn_match:
            fn_name = fn_match.group(1)
            # check if defined in html script
            is_defined = f'function {fn_name}' in html or f'{fn_name} =' in html or f'{fn_name}=' in html
            if not is_defined:
                print(f"❌ MISSING JS FUNCTION: {fn_name} (from onclick=\"{oc}\")")
            else:
                pass
                
    # find all getElementById inside modal
    ids_in_modal = re.findall(r'id=["\']([^"\']+)["\']', modal_content)
    print(f"Total IDs in {m}: {len(ids_in_modal)}")
