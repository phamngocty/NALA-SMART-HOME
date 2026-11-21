with open('scratch/aiConfigModal_original.html', 'r', encoding='utf-8') as f:
    text = f.read()

# find modal-body
start_mb = text.find('<div class="modal-body"')
if start_mb != -1:
    # find where modal-body ends (before modal-footer or close)
    end_mb = text.rfind('<div class="modal-footer"')
    print(f"modal-body from {start_mb} to {end_mb}")
    inner_body = text[start_mb:end_mb]
    with open('scratch/ai_modal_inner_body.html', 'w', encoding='utf-8') as out:
        out.write(inner_body)
    print("Saved inner body length:", len(inner_body))
