import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'function escapeHtml' in line or 'const escapeHtml' in line or 'let escapeHtml' in line:
            print(f'{i+1}: {line.strip()}')
