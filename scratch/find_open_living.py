with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('function openLivingContextAutomationModal')
if idx != -1:
    print(html[idx:idx+600])
else:
    print("function openLivingContextAutomationModal not found!")
