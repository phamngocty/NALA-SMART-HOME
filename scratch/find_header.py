with open('server_nas_hub/app/static/index.html', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines[:3700]):
    if any(k in line for k in ['<header', '<nav', 'class="container', 'id="container', 'class="main', 'id="header', 'class="top-bar', 'class="navbar', '<h1', '<h2', '<h3', 'class="box', 'class="section']):
        print(f"Line {i+1}: {line.strip()[:100]}")
