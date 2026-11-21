with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

idx_lc = text.find('id="livingContextAutomationModal"')
print("=== livingContextAutomationModal ===")
print(text[idx_lc:idx_lc+3500])

idx_comm = text.find('id="communicationModal"')
print("\n=== communicationModal ===")
print(text[idx_comm:idx_comm+3500])
