import sys, json
sys.stdout.reconfigure(encoding='utf-8')

with open('c:/Users/phamn/.gemini/antigravity/brain/32900fef-234a-4ca1-ba91-1037432aee9f/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        obj = json.loads(line)
        idx = obj.get('step_index')
        tcs = obj.get('tool_calls')
        if tcs and idx in [5008, 5010, 5012, 5048, 5052, 5054]:
            tc = tcs[0]
            print(f"=== STEP {idx} ===")
            print("Target:\n", tc['args'].get('Target'))
            print("Replacement:\n", tc['args'].get('Replacement'))
            print("-" * 40)
