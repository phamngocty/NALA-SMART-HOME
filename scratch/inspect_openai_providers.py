with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    text = f.read()

p = text.find('elif prov == "groq":')
print(text[p:p+2000])
