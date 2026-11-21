with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

ids_to_check = [
    'autoEditRuleId',
    'autoEditorBadge',
    'autoEditName',
    'autoEditDesc',
    'autoEditTriggerState',
    'autoEditTargetRoom',
    'autoEditTimeStart',
    'autoEditTimeEnd',
    'autoEditMaxLux',
    'autoEditClimateAction',
    'autoEditClimateTempWrap',
    'autoEditClimateTemp',
    'autoEditLightAction',
    'autoEditEnabled',
    'autoBtnDelete'
]

print("=== CHECKING AUTOMATION EDITOR ELEMENT IDS ===")
for eid in ids_to_check:
    print(f"ID '{eid}': {'EXISTS' if f'id=\"{eid}\"' in html else '❌ MISSING!'}")
