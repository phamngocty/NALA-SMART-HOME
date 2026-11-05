with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

ids = ['kpiTotal', 'kpiOnline', 'kpiPaired', 'kpiUnpaired', 'unpairedCount', 'unpairedGrid', 'pairedCount', 'pairedGrid', 'wsDot', 'wsText', 'haDot', 'haText']
for el_id in ids:
    found = f'id="{el_id}"' in content or f"id='{el_id}'" in content
    print(f'{el_id}: found={found}')
