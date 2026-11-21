with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('voice_persona')
print("Found voice_persona in ai_agent_router.py at:", idx)
if idx != -1:
    print(content[idx-100:idx+600])
