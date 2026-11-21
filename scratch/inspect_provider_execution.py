with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    text = f.read()

# find where candidates are called in process_intent
p = text.find('for prov_idx, prov in enumerate(candidates):')
print("=== process_intent provider call ===")
print(text[p:p+1800])
