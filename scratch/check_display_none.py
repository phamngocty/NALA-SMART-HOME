with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Check tab_vp_enroll and tab_vp_history display
idx1 = content.find('id="sub_vp_live_panel"')
print("sub_vp_live_panel chunk:")
print(content[idx1:idx1+300])

idx2 = content.find('id="sub_vp_hist_panel"')
print("\nsub_vp_hist_panel chunk:")
print(content[idx2:idx2+300])
