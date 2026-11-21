import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html.bak_v306', 'r', encoding='utf-8') as f:
    text = f.read()

# Test extracting haConfigModal body
ha_body = re.search(r'<div class="modal-body"[^>]*>.*?</div>\s*<div class="modal-footer".*?</div>', text[text.find('id="haConfigModal"'):text.find('id="otaManagerModal"')], re.DOTALL)
print("HA body found:", bool(ha_body), len(ha_body.group(0)) if ha_body else 0)

# Test extracting otaManagerModal body
ota_body = re.search(r'<div class="modal-body"[^>]*>.*?</div>\s*<div class="modal-footer".*?</div>', text[text.find('id="otaManagerModal"'):text.find('id="intercomModal"')], re.DOTALL)
print("OTA body found:", bool(ota_body), len(ota_body.group(0)) if ota_body else 0)

# Test extracting intercomModal body
intercom_body = re.search(r'<div class="modal-body"[^>]*>.*?</div>\s*<div class="modal-footer".*?</div>', text[text.find('id="intercomModal"'):text.find('id="historyModal"')], re.DOTALL)
print("Intercom body found:", bool(intercom_body), len(intercom_body.group(0)) if intercom_body else 0)

# Test extracting historyModal body
history_body = re.search(r'<div class="modal-body"[^>]*>.*?</div>\s*<div class="modal-footer".*?</div>', text[text.find('id="historyModal"'):text.find('id="voiceprintModal"')], re.DOTALL)
print("History body found:", bool(history_body), len(history_body.group(0)) if history_body else 0)

# Test extracting aiConfigModal body
ai_body = re.search(r'<div class="modal-body"[^>]*>.*?</div>\s*<div class="modal-footer".*?</div>', text[text.find('id="aiConfigModal"'):text.find('id="nalaMemoryModal"')], re.DOTALL)
print("AI body found:", bool(ai_body), len(ai_body.group(0)) if ai_body else 0)

# Test extracting nalaMemoryModal body
mem_body = re.search(r'(<!-- Metric Badges & Action Bar -->.*?<div class="modal-footer".*?</div>)', text[text.find('id="nalaMemoryModal"'):text.find('id="allHouseConfigModal"')], re.DOTALL)
print("Memory body found:", bool(mem_body), len(mem_body.group(0)) if mem_body else 0)
