with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('async def get_ai_models(')
print(repr(content[idx:idx+350]))
