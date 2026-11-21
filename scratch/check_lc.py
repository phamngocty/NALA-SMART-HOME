with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

m1 = text.find('id="tab_lc_fsm"')
m2 = text.find('id="tab_lc_rules"')
print('tab_lc_fsm:', text[m1:m1+300])
print('tab_lc_rules:', text[m2:m2+300])
