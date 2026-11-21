import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

matches = [m for m in re.findall(r'id="([^"]+)"', content) if any(k in m.lower() for k in ['tts', 'voice', 'persona', 'vad', 'pitch', 'rate'])]
print("Found element IDs related to voice/persona:")
for m in set(matches):
    print(" -", m)

# Also check for tabs inside systemSettingsModal or other modals
tab_matches = re.findall(r'id="(tab_[^"]+)"', content)
print("\nTabs in index.html:")
for t in set(tab_matches):
    print(" -", t)
