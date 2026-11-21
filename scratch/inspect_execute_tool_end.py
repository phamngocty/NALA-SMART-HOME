with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def execute_tool')
print(content[idx+2000:idx+4000])
