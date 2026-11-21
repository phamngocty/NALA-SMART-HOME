import subprocess, re

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

for m in re.finditer(r'id=["\']([a-zA-Z0-9_]*Modal)["\']', text):
    print(f"Modal: {m.group(1)} at {m.start()}")

# Find loadAIConfig
p = text.find('loadAIConfig')
print("loadAIConfig in text:", p)
if p != -1:
    print(text[p-50:p+500])
