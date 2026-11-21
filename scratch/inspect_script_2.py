import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
s2 = scripts[2]
lines = s2.splitlines()

for i in range(1820, 1850):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}")
