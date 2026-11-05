import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'openOTAManagerModal' in line or 'otaModal' in line or 'Chọn tệp' in line:
            print(f'{i+1}: {line.strip()[:100]}')
