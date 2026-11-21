with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Check systemSettingsModal div nesting
start_line = 2100
end_line = 3190

depth = 0
for i in range(start_line, end_line):
    line = lines[i]
    opens = line.count('<div')
    closes = line.count('</div')
    depth += opens - closes
    if any(t in line for t in ['id="systemSettingsModal"', 'class="modal-body"', 'id="tab_sys_role"', 'id="tab_sys_ai"', 'id="tab_sys_ext"', 'id="tab_sys_ha"', 'id="tab_sys_ota"', 'class="modal-footer"']):
        print(f"Line {i+1} (depth={depth}): {line.strip()[:100]}")
