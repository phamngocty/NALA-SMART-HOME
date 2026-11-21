with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('id="automationEditorModal"')
print("automationEditorModal idx:", idx)
if idx != -1:
    print(html[idx:idx+1500])

idx_fn = html.find('function openAutomationEditorModal')
print("\nopenAutomationEditorModal idx:", idx_fn)
if idx_fn != -1:
    print(html[idx_fn:idx_fn+600])
