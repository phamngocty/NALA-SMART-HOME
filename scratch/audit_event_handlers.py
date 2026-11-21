import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

slices = {
    'userProfileMemoryModal': (63252, 90626),
    'livingContextAutomationModal': (90626, 96413),
    'communicationModal': (96413, 108957),
    'systemSettingsModal': (108957, 160000)
}

js_funcs = set(re.findall(r'(?:function|async\s+function)\s+([a-zA-Z0-9_]+)\s*\(', text))

for name, (start, end) in slices.items():
    chunk = text[start:end]
    handlers = re.findall(r'(?:onclick|onchange|oninput)=["\']([^"\']+)["\']', chunk)
    print(f"\n=== Modal: {name} (handlers: {len(handlers)}) ===")
    missing_handlers = set()
    for h in handlers:
        calls = re.findall(r'([a-zA-Z0-9_]+)\s*\(', h)
        for c in calls:
            if c in ['alert', 'confirm', 'parseInt', 'parseFloat', 'event', 'stopPropagation', 'getElementById', 'if']:
                continue
            if c not in js_funcs:
                missing_handlers.add(c)
    if missing_handlers:
        print(f"  ❌ MISSING FUNCTIONS: {missing_handlers}")
    else:
        print("  ✅ All event handlers valid!")
