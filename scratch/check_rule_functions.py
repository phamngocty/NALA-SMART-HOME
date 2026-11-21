with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

funcs = [
    'toggleRuleState',
    'editAutomationRule',
    'deleteAutomationRule',
    'openAutomationEditorModal',
    'closeAutomationEditorModal',
    'saveAutomationRule'
]

for fn in funcs:
    idx = text.find(f'function {fn}')
    if idx == -1:
        idx = text.find(f'async function {fn}')
    print(f"Function {fn}: {'FOUND at ' + str(idx) if idx != -1 else '❌ NOT FOUND!'}")
    if idx != -1:
        print(text[idx:idx+400])
        print("="*40)
