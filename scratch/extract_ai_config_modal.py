import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

p = text.find('id="aiConfigModal"')
p_end = text.find('id="allHouseConfigModal"', p)
print("Length of aiConfigModal:", p_end - p)
with open('scratch/aiConfigModal_original.html', 'w', encoding='utf-8') as f:
    f.write(text[p:p_end])
print("Saved to scratch/aiConfigModal_original.html")
