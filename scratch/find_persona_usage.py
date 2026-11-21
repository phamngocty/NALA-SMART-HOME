with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = re.findall(r'def [^\(]+prompt[^\(]*\(', content)
print("Functions with prompt:", matches)

matches2 = [m.start() for m in re.finditer(r'voice_persona', content)]
print("voice_persona occurrences at:", matches2)
for pos in matches2:
    print("--- snippet ---")
    print(content[pos-50:pos+150])
