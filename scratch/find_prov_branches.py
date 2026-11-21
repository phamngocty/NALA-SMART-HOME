with open('server_nas_hub/app/ai_agent_router.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'prov ==' in l or 'prov in' in l:
        print(f"{i+1}: {l.strip()}")
