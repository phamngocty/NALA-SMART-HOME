import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

p_ota = text.find('id="otaManagerModal"')
p_intercom = text.find('id="intercomModal"')
print("Length of otaManagerModal in HEAD~2:", p_intercom - p_ota)

with open('scratch/otaManagerModal_original.html', 'w', encoding='utf-8') as f:
    f.write(text[p_ota:p_intercom])

print("Saved scratch/otaManagerModal_original.html!")
