with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('id="tab_lc_rules"')
print("=== tab_lc_rules HTML ===")
print(text[idx:idx+2000])

idx_js = text.find('function loadAutomationRules')
if idx_js == -1:
    idx_js = text.find('async function loadAutomationRules')
print("\n=== loadAutomationRules JS ===")
print(text[idx_js:idx_js+2500])
