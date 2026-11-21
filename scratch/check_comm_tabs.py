with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="communicationModal"')
end = html.find('id="systemSettingsModal"')
modal_text = html[start:end]

for tab in ['intercom', 'history']:
    btn = f'id="tab_comm_{tab}_btn"' in modal_text
    div = f'id="tab_comm_{tab}"' in modal_text
    print(f"COMM tab '{tab}': btn={btn}, div={div}")

idx = html.find('function openCommunicationModal')
print("\n--- openCommunicationModal & switchCommunicationTab ---")
print(html[idx:idx+600])
