with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. userProfileMemoryModal
start = html.find('id="userProfileMemoryModal"')
end = html.find('id="livingContextAutomationModal"')
print("=== userProfileMemoryModal (length:", end - start, ") ===")
# print first 1500 chars
print(html[start:start+1500])

# 2. livingContextAutomationModal
start_lc = html.find('id="livingContextAutomationModal"')
end_lc = html.find('id="communicationModal"')
print("\n=== livingContextAutomationModal (length:", end_lc - start_lc, ") ===")
print(html[start_lc:end_lc])
