with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

p = html.find('name="aiProviderRadio"')
print(html[p-300:p+1500])
