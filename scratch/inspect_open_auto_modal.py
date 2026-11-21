with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_js = text.find('function openAutomationEditorModal')
print(text[idx_js:idx_js+2500])
