with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

idx = html.find('function openUserProfileMemoryModal')
if idx != -1:
    print(html[idx:idx+1200])

start = html.find('id="userProfileMemoryModal"')
idx_tabs = html.find('class="wizard-tabs"', start)
print("\n--- Wizard tabs in userProfileMemoryModal ---")
print(html[idx_tabs:idx_tabs+1200])
