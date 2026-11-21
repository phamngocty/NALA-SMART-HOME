with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('async function loadAutomationRules')
print(text[idx:idx+4500])
