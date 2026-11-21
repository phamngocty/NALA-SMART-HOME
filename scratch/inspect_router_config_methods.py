with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx1 = text.find('def _load_initial_config(')
idx2 = text.find('def list_available_models(', idx1)
print(text[idx1:idx2])
