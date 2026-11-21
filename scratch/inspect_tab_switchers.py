with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = [
    'switchUserProfileMemoryTab',
    'switchLivingContextTab',
    'switchCommunicationTab',
    'switchSystemSettingsTab',
    'switchVoiceprintSubTab',
    'openUserProfileMemoryModal',
    'openLivingContextModal',
    'openCommunicationModal',
    'openSystemSettingsModal'
]

for func in funcs:
    idx = text.find(f'function {func}')
    if idx != -1:
        print(f"=== FUNCTION {func} ===")
        print(text[idx:idx+800])
        print("\n" + "="*40 + "\n")
    else:
        print(f"NOT FOUND: {func}")
