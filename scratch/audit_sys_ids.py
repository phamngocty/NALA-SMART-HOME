with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

ids_to_check = [
    # Role
    'xzVoiceDropdownContainer', 'xzSelectedVoiceName', 'xzVoiceMenu', 'xzRolePersona',
    'xzSpeakingRate', 'xzSpeakingPitch', 'xzVadSpeed',
    # AI
    'cfgGeminiKey', 'cfgGroqKey', 'cfgDeepseekKey', 'cfgOpenrouterKey',
    # HA
    'haWsUrlInput', 'haTokenInput', 'haModalStatusBadge',
    # OTA
    'otaFileInput', 'otaVersionInput'
]

print("=== CHECKING ESSENTIAL DOM IDS ===")
for el_id in ids_to_check:
    found = f'id="{el_id}"' in html
    print(f"ID {el_id}: {'✅ OK' if found else '❌ MISSING'}")
