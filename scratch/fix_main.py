with open('firmware_esp32s3_panel/src/main.cpp', 'r', encoding='utf-8') as f:
    c = f.read()

target = '''            if (st.containsKey("room_view_timeout")) {
                uint8_t to = st["room_view_timeout"] | nvsStore.get().room_view_timeout;
                if (to != nvsStore.get().room_view_timeout) {
                    nvsStore.get().room_view_timeout = to;
                    if (taken) uiDashboard.set_room_view_timeout(to);
                    changed = true;
                }
            }'''

c_norm = c.replace('\r\n', '\n')
t_norm = target.replace('\r\n', '\n')

if t_norm in c_norm:
    c_norm = c_norm.replace(t_norm, '')
    with open('firmware_esp32s3_panel/src/main.cpp', 'w', encoding='utf-8') as f:
        f.write(c_norm)
    print('Removed set_room_view_timeout call from main.cpp successfully!')
else:
    print('Target not found!')
