with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="userProfileMemoryModal"')
end = html.find('id="livingContextAutomationModal"')
modal_text = html[start:end]

for tab in ['members', 'voiceprint', 'memory', 'test']:
    btn = f'id="tab_upm_{tab}_btn"' in modal_text
    div = f'id="tab_upm_{tab}"' in modal_text
    print(f"UPM tab '{tab}': btn={btn}, div={div}")
