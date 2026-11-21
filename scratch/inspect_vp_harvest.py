with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('# Thu hoạch kết quả nhận diện vân giọng')
print(content[idx:idx+1500])
