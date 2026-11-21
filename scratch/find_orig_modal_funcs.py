import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

for name in ['function openHAConfigModal', 'function openOTAManagerModal', 'function openAIConfigModal', 'function openHistoryModal', 'function openIntercomModal']:
    p = text.find(name)
    if p != -1:
        print(f"=== {name} ===")
        print(text[p:p+500])
