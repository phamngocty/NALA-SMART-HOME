with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
scripts = list(re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE))
for i, m in enumerate(scripts):
    if 'playVoicePreviewItem' in m.group(1):
        print(f"Found playVoicePreviewItem in script block {i}")
        # check if async is there
        idx = m.group(1).find('playVoicePreviewItem')
        print(m.group(1)[idx-20:idx+40])
