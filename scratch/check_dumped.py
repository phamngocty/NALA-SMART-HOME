import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('scratch/dumped_dom.html', 'r', encoding='utf-8') as f:
    text = f.read()

keywords = ['wsText', 'haStatusText', 'kpiTotal', 'kpiOnline', 'pairedGrid']
for kw in keywords:
    idx = text.find(kw)
    if idx != -1:
        snippet = text[max(0, idx - 50):min(len(text), idx + 200)]
        print(f'=== {kw} ===\n{snippet}\n')
