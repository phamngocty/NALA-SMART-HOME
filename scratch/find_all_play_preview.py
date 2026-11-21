with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
scripts = list(re.finditer(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE))
s = scripts[2].group(1)
for m in re.finditer(r'.{0,30}playVoicePreviewItem.{0,30}', s):
    print("Match:", m.group(0))
