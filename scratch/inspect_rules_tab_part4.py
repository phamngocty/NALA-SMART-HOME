with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_js = text.find('async function loadAutomationRules')
print(text[idx_js+5000:idx_js+7500])
