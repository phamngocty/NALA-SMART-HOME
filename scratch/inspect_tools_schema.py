with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('def _get_ha_tools_schema_openai')
if idx != -1:
    print(content[idx:idx+3500])
