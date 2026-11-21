import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout

p_intercom = text.find('id="intercomModal"')
p_history = text.find('id="historyModal"')
p_climate = text.find('id="climateModal"')

print("Length of intercomModal in HEAD~2:", p_history - p_intercom)
print("Length of historyModal in HEAD~2:", p_climate - p_history)

with open('scratch/intercomModal_original.html', 'w', encoding='utf-8') as f:
    f.write(text[p_intercom:p_history])

with open('scratch/historyModal_original.html', 'w', encoding='utf-8') as f:
    f.write(text[p_history:p_climate])

print("Saved scratch/intercomModal_original.html and scratch/historyModal_original.html!")
