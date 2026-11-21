with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('function onAIProviderChanged')
print("onAIProviderChanged:")
print(html[idx:idx+800])

idx_save = html.find('async function saveAIConfig')
if idx_save == -1:
    idx_save = html.find('function saveAIConfig')
print("\nsaveAIConfig:")
print(html[idx_save:idx_save+800])
