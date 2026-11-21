with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# Test the automation functions block
start_idx = text.find('async function loadAutomationRules()')
end_idx = text.find('// HUB 4: CÀI ĐẶT KỸ THUẬT', start_idx)
block = text[start_idx:end_idx]

print("=== CHECKING VARIABLE USAGE IN AUTOMATION FUNCTIONS ===")
# extract identifiers
words = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', block))
print("Identifiers in block:", len(words))

# Check for words that look like global variables
suspects = [w for w in words if not w.startswith('_') and len(w) > 3]
for s in suspects:
    # check if declared
    is_declared = re.search(rf'\b(let|var|const|function|async\s+function)\s+{s}\b', text) is not None
    if not is_declared and s not in [
        'document', 'window', 'console', 'fetch', 'alert', 'confirm',
        'JSON', 'Object', 'Set', 'Array', 'Math', 'parseFloat', 'parseInt',
        'true', 'false', 'null', 'undefined', 'length', 'push', 'join',
        'map', 'forEach', 'find', 'entries', 'has', 'add', 'value', 'checked',
        'style', 'display', 'innerHTML', 'textContent', 'className', 'classList',
        'method', 'headers', 'body', 'domain', 'service', 'temperature', 'status',
        'rules', 'rule', 'ruleId', 'name', 'description', 'trigger', 'state',
        'conditions', 'actions', 'target_room', 'time_range', 'max_lux', 'occupant',
        'brightness_pct', 'climate', 'light', 'none', 'set_temp', 'turn_off',
        'dim_10', 'dim_30', 'dim_50', 'turn_on_100', 'enabled', 'start', 'end',
        'deep_sleep', 'night_wakeup', 'empty', 'active', 'approaching', 'all',
        'createElement', 'appendChild', 'focus', 'remove', 'catch', 'error',
        'message', 'target', 'event'
    ]:
        print(f"  Suspect undeclared: {s}")
