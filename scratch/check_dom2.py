import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scratch/dumped_dom2.html', 'r', encoding='utf-8') as f:
    text = f.read()

keywords = ['otaFileInput', '881C', 'D6F4', 'v2.7.6']
for kw in keywords:
    idx = text.find(kw)
    print(f'{kw}: found={idx != -1}')
