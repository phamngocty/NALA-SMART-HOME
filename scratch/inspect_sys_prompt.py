with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def _build_system_prompt')
if idx != -1:
    print(content[idx:idx+1500])
else:
    print("def _build_system_prompt not found")
