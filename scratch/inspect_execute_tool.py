with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def execute_tool')
if idx != -1:
    print(content[idx:idx+2500])
