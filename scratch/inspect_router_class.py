with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('class AIAgentRouter')
print(content[idx:idx+1200])
