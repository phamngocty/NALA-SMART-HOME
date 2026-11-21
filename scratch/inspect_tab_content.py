with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

p_ha = text.find('id="tab_sys_ha"')
p_ai = text.find('id="tab_sys_ai"')
p_ota = text.find('id="tab_sys_ota"')
p_end = text.find('id="automationEditorModal"')

print("HA len:", p_ai - p_ha)
print("AI len:", p_ota - p_ai)
print("OTA len:", p_end - p_ota)

print("--- AI HEAD ---")
print(text[p_ai:p_ai+400])
