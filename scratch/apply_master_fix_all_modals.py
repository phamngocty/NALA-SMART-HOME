import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

print("Original index.html length:", len(text))

# -------------------------------------------------------------------------
# 1. READ ORIGINAL INNER BODIES
# -------------------------------------------------------------------------
with open('scratch/haConfigModal_original.html', 'r', encoding='utf-8') as f:
    ha_raw = f.read()
ha_start = ha_raw.find('<div class="modal-body"')
ha_end = ha_raw.find('<div class="modal-footer"')
ha_inner = ha_raw[ha_start:ha_end]
ha_footer_start = ha_raw.find('<button type="button" class="btn-cancel" onclick="testHAConnectionFromModal()"')
ha_footer_end = ha_raw.find('</div>\n        </div>\n    </div>')
ha_actions = ha_raw[ha_footer_start:ha_footer_end]

with open('scratch/otaManagerModal_original.html', 'r', encoding='utf-8') as f:
    ota_raw = f.read()
ota_start = ota_raw.find('<div class="modal-body"')
ota_end = ota_raw.find('<div class="modal-footer"')
ota_inner = ota_raw[ota_start:ota_end]

with open('scratch/intercomModal_original.html', 'r', encoding='utf-8') as f:
    intercom_raw = f.read()
intercom_start = intercom_raw.find('<div class="modal-body"')
intercom_end = intercom_raw.find('<div class="modal-footer"')
intercom_inner = intercom_raw[intercom_start:intercom_end]

with open('scratch/historyModal_original.html', 'r', encoding='utf-8') as f:
    hist_raw = f.read()
hist_start = hist_raw.find('<div class="modal-body"')
hist_end = hist_raw.find('<div class="modal-footer"')
hist_inner = hist_raw[hist_start:hist_end]

# -------------------------------------------------------------------------
# 2. REBUILD systemSettingsModal (Tab HA & Tab OTA)
# -------------------------------------------------------------------------
# In systemSettingsModal:
# Find tab_sys_ha to end of tab_sys_ota
p_ha = text.find('<div id="tab_sys_ha"')
p_ota_div = text.find('<div id="tab_sys_ota"')
p_sys_footer = text.find('<div class="modal-footer"', p_ota_div)
assert p_ha != -1 and p_ota_div != -1 and p_sys_footer != -1, "Could not locate tab_sys_ha or tab_sys_ota"

# Complete HA Tab Content
tab_ha_complete = f'''<div id="tab_sys_ha" style="display: none;">
    {ha_inner}
    <div style="padding: 0 24px 24px 24px; display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 16px;">
        <button type="button" class="btn-cancel" onclick="testHAConnectionFromModal()" style="border: 1px solid rgba(56, 189, 248, 0.4); color: #38bdf8; background: rgba(56, 189, 248, 0.1); cursor: pointer; padding: 8px 16px; border-radius: 8px; font-weight: 600;">
            🔍 Kiểm Tra Kết Nối (Test Live)
        </button>
        <button type="button" class="btn-save-all" onclick="saveHAConfigFromModal()" style="background: linear-gradient(135deg, #0284c7, #06b6d4); color: white; border: none; padding: 9px 22px; border-radius: 8px; font-weight: 700; cursor: pointer;">
            💾 Lưu &amp; Kết Nối Lại
        </button>
    </div>
</div>\n'''

# Complete OTA Tab Content
tab_ota_complete = f'''<div id="tab_sys_ota" style="display: none;">
    {ota_inner}
</div>\n'''

text = text[:p_ha] + tab_ha_complete + tab_ota_complete + text[p_sys_footer:]
print("Updated systemSettingsModal HA & OTA tabs!")

# -------------------------------------------------------------------------
# 3. VERIFY & SAVE
# -------------------------------------------------------------------------
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved updated index.html! New length:", len(text))
