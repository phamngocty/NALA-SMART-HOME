with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('submitMultiSlotEnroll')
if idx != -1:
    print(content[idx:idx+2000])
else:
    print("submitMultiSlotEnroll not found")
