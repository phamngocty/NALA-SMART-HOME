with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def save_config(')
print(content[idx:idx+1500])
