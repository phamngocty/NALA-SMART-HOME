import subprocess, re

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

# Look for functions that fetch /api/ha, /api/ota, /api/ai
for m in re.finditer(r'function\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{[^}]*fetch\(["\']/api/(ha|ota|ai)[^"\']*["\']', text):
    print("Found function:", m.group(1))

# Search for openHAConfigModal, openOTAManagerModal, openAIConfigModal
for name in ['openHAConfigModal', 'openOTAManagerModal', 'openAIConfigModal']:
    p = text.find(name)
    if p != -1:
        print(f"--- {name} in HEAD~2 ---")
        print(text[p:p+500])
