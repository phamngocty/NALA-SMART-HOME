with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = text.find('class AIAgentRouter:')
print(text[idx:idx+1500])
