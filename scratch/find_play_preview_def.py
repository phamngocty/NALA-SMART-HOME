with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
scripts = list(re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE))
s = scripts[2].group(1)
idx = s.find('playVoicePreviewItem(')
print("Def:", s[idx-15:idx+35])
