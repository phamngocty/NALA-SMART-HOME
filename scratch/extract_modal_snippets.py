import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

def get_modal_snippet(modal_id):
    pattern = rf'(<div[^>]*class=["\'][^"\']*modal-overlay[^"\']*["\'][^>]*id=["\']{modal_id}["\'].*?)(?=<div[^>]*class=["\'][^"\']*modal-overlay|\Z)'
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return None

for mid in ['haConfigModal', 'otaManagerModal', 'intercomModal', 'historyModal', 'voiceprintModal', 'aiConfigModal', 'nalaMemoryModal']:
    snip = get_modal_snippet(mid)
    if snip:
        print(f"Found {mid}: {len(snip)} chars, ends with: {snip[-40:].replace(chr(10), ' ')}")
    else:
        print(f"NOT FOUND: {mid}")
