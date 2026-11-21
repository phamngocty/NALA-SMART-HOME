with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. HA
p1 = html.find('async function openHAConfigModal')
if p1 != -1:
    print("HA config body:")
    print(html[p1:p1+800])

# 2. AI
p2 = html.find('function openAIConfigModal')
if p2 != -1:
    print("\nAI config body:")
    print(html[p2:p2+800])
