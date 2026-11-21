with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

start = html.find('id="tab_sys_ota"')
end = html.find('id="automationEditorModal"', start)
print(html[start:start+1800])
