with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('async function saveAutomationRule()')
if idx == -1:
    idx = text.find('function saveAutomationRule()')
print(text[idx:idx+3500])
