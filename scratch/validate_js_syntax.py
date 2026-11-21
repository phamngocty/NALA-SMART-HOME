import re
import subprocess
import os

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Find all script contents (ignoring type="module" or src="...")
scripts = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)

print(f"Found {len(scripts)} inline script blocks.")

for i, s in enumerate(scripts):
    temp_file = f"scratch/test_script_{i}.js"
    with open(temp_file, 'w', encoding='utf-8') as f_out:
        f_out.write(s)
    
    res = subprocess.run(['node', '--check', temp_file], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Script {i} has syntax error:")
        print(res.stderr[:500])
    else:
        print(f"✅ Script {i} passed syntax check.")
    
    if os.path.exists(temp_file):
        os.remove(temp_file)
