with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = re.findall(r'switchVoiceprintTab\([^)]*\)', html)
print("Occurrences of switchVoiceprintTab:", matches)
print("Definition of switchVoiceprintTab exists?:", 'function switchVoiceprintTab' in html)
