with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

m1 = text.find('id="tab_comm_intercom"')
m2 = text.find('id="tab_comm_history"')
print('tab_comm_intercom:', text[m1:m1+300])
print('tab_comm_history:', text[m2:m2+300])
