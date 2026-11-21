with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('async async function enrollSelectedHistoryRecordings', 'async function enrollSelectedHistoryRecordings')

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed double async!")
