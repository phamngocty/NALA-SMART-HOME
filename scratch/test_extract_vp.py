import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('server_nas_hub/app/static/index.html.bak_v306', 'r', encoding='utf-8') as f:
    text = f.read()

vp_chunk = text[text.find('id="voiceprintModal"'):text.find('id="automationEditorModal"')]

def extract_tab(tab_id, next_tab_id):
    start = vp_chunk.find(f'id="{tab_id}"')
    if start == -1: return None
    # find open div before id
    div_start = vp_chunk.rfind('<div', 0, start)
    if next_tab_id:
        end = vp_chunk.find(f'id="{next_tab_id}"')
        div_end = vp_chunk.rfind('<!-- TAB', 0, end)
        if div_end == -1: div_end = vp_chunk.rfind('<div', 0, end)
        return vp_chunk[div_start:div_end].strip()
    else:
        # last tab: before modal-footer
        end = vp_chunk.find('class="modal-footer"')
        div_end = vp_chunk.rfind('</div>', 0, end)
        return vp_chunk[div_start:div_end].strip()

t_speakers = extract_tab('tab_vp_speakers', 'tab_vp_enroll')
t_enroll = extract_tab('tab_vp_enroll', 'tab_vp_history')
t_history = extract_tab('tab_vp_history', 'tab_vp_test')
t_test = extract_tab('tab_vp_test', 'tab_vp_context')
t_context = extract_tab('tab_vp_context', None)

print("Speakers:", bool(t_speakers), len(t_speakers) if t_speakers else 0)
print("Enroll:", bool(t_enroll), len(t_enroll) if t_enroll else 0)
print("History:", bool(t_history), len(t_history) if t_history else 0)
print("Test:", bool(t_test), len(t_test) if t_test else 0)
print("Context:", bool(t_context), len(t_context) if t_context else 0)
