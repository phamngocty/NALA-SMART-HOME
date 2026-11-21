with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

import re
for m in re.finditer(r'.{0,40}saveMultiSlotVoiceprint.{0,40}', content):
    print("Match:", m.group(0))
