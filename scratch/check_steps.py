import json

with open('c:/Users/phamn/.gemini/antigravity/brain/32900fef-234a-4ca1-ba91-1037432aee9f/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        if idx in range(6412, 6453):
            if 'tool_calls' in obj:
                for tc in obj['tool_calls']:
                    print(f"Step {idx}: {tc.get('name')} | {str(tc.get('args'))[:120]}")
