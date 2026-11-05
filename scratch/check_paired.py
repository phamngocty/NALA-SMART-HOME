import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scratch/dumped_dom.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="pairedGrid"')
if idx != -1:
    print(text[idx:idx+1500])
