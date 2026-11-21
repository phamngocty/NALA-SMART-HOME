with open('server_nas_hub/app/voiceprint_manager.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace('from typing import Optional, Tuple, List, Dict', 'from typing import Optional, Tuple, List, Dict, Any')

with open('server_nas_hub/app/voiceprint_manager.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("✅ Added Any to typing imports in voiceprint_manager.py!")
