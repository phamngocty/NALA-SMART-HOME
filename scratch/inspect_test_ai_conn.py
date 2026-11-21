with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('async function testAIConn')
if p == -1:
    p = html.find('function testAIConn')
print(html[p:p+1200])
