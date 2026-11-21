with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="tab_sys_role"')
role_chunk = text[idx:idx+8000]
import re
inputs = re.findall(r'<input[^>]*type=["\']range["\'][^>]*>', role_chunk)
for inp in inputs:
    print(inp)
