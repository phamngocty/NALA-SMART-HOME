import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

p_ha = text.find('id="haConfigModal"')
p_ota = text.find('id="otaManagerModal"')
print("Length of haConfigModal in HEAD~2:", p_ota - p_ha)

with open('scratch/haConfigModal_original.html', 'w', encoding='utf-8') as f:
    f.write(text[p_ha:p_ota])

print("Saved scratch/haConfigModal_original.html!")
