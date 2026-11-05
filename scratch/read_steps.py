import sys, json
sys.stdout.reconfigure(encoding='utf-8')
with open(r'C:\Users\phamn\.gemini\antigravity\brain\32900fef-234a-4ca1-ba91-1037432aee9f\.system_generated\logs\transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        o = json.loads(line)
        if o.get('source') == 'USER_EXPLICIT':
            c = o.get('content', '') or ''
            print(f"Step {o.get('step_index')}: {c[:80]}")
