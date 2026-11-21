import re

filepath = 'server_nas_hub/app/static/index.html'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Read ai_modal_inner_body.html
with open('scratch/ai_modal_inner_body.html', 'r', encoding='utf-8') as f:
    ai_body = f.read()

# 2. Insert tab_sys_ai right before <div id="tab_sys_ha"
tab_ai_full = f'''<div id="tab_sys_ai" style="display: none;">
    {ai_body}
</div>\n'''

p_ha = text.find('<div id="tab_sys_ha"')
assert p_ha != -1, "Could not find <div id=\"tab_sys_ha\""
text = text[:p_ha] + tab_ai_full + text[p_ha:]

# 3. Add chkMemoryEnabled in tab_upm_memory Action Bar
chk_html = '''<label style="display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700; color: #38bdf8; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 6px; cursor: pointer;">
                    <input type="checkbox" id="chkMemoryEnabled" onchange="toggleMemoryEnabled(this.checked)" style="accent-color: #38bdf8; cursor: pointer;" checked>
                    <span>Tự Học Adaptive Memory</span>
                </label>'''

target_bar = '<div style="display: flex; gap: 8px;">'
p_bar = text.find(target_bar, text.find('id="tab_upm_memory"'))
if p_bar != -1:
    text = text[:p_bar + len(target_bar)] + "\n                " + chk_html + text[p_bar + len(target_bar):]

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Saved updated index.html! New length:", len(text))
