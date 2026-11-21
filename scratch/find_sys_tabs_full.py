with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_sys = text.find('id="systemSettingsModal"')
end_sys = text.find('<!-- END systemSettingsModal', idx_sys)
if end_sys == -1:
    # search for closing </div>
    print("No end comment. Length from idx_sys to end of file:", len(text) - idx_sys)

import re
matches = re.findall(r'id=["\'](tab_sys_[a-zA-Z0-9_]+)["\']', text[idx_sys:])
print("Matches for tab_sys_ after systemSettingsModal:", set(matches))
