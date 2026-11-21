with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Check DEFAULT_CONFIG
idx = text.find('DEFAULT_CONFIG = {')
print(text[idx:idx+1200])
