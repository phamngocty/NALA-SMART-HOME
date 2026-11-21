import re

with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

modals = [
    {
        "id": "userProfileMemoryModal",
        "name": "👤 Hồ Sơ & Trí Nhớ",
        "open_fn": "openUserProfileMemoryModal",
        "switch_fn": "switchUserProfileMemoryTab",
        "expected_tabs": ["members", "voiceprint", "memory", "test"]
    },
    {
        "id": "livingContextAutomationModal",
        "name": "🌙 Tự Động Hóa Ngữ Cảnh",
        "open_fn": "openLivingContextAutomationModal",
        "switch_fn": "switchLivingContextTab",
        "expected_tabs": ["fsm", "rules"]
    },
    {
        "id": "communicationModal",
        "name": "🎙️ Giao Tiếp & Lịch Sử",
        "open_fn": "openCommunicationModal",
        "switch_fn": "switchCommunicationTab",
        "expected_tabs": ["intercom", "history"]
    },
    {
        "id": "systemSettingsModal",
        "name": "⚙️ Cài Đặt Kỹ Thuật",
        "open_fn": "openSystemSettingsModal",
        "switch_fn": "switchSystemSettingsTab",
        "expected_tabs": ["role", "ai", "ext", "ha", "ota"]
    }
]

print("=== AUDIT OF ALL 4 HUBS IN INDEX.HTML ===")
for m in modals:
    print(f"\n--- Checking {m['name']} (id='{m['id']}') ---")
    idx = html.find(f'id="{m["id"]}"')
    if idx == -1:
        print(f"❌ MODAL {m['id']} NOT FOUND IN HTML!")
        continue
    print(f"✅ Modal {m['id']} found at pos {idx}")

    # Check open function
    if f"function {m['open_fn']}" in html:
        print(f"✅ Open function '{m['open_fn']}' defined")
    else:
        print(f"❌ Open function '{m['open_fn']}' MISSING!")

    # Check switch function
    if f"function {m['switch_fn']}" in html:
        print(f"✅ Switch function '{m['switch_fn']}' defined")
    else:
        print(f"❌ Switch function '{m['switch_fn']}' MISSING!")

    # Check tabs inside modal
    # Extract modal content
    modal_end = html.find('</div>\n</div>', idx)
    modal_chunk = html[idx:idx+35000] # large enough

    for t in m["expected_tabs"]:
        # Check tab button
        btn_pattern = rf'id="tab_[a-z]+_{t}_btn"'
        btn_match = re.search(btn_pattern, modal_chunk)
        if btn_match:
            print(f"  ✅ Tab button: {btn_match.group(0)}")
        else:
            print(f"  ❌ Tab button for '{t}' NOT FOUND!")

        # Check tab content pane
        pane_pattern = rf'id="tab_[a-z]+_{t}"'
        pane_match = re.search(pane_pattern, modal_chunk)
        if pane_match:
            # Check style
            pane_id = pane_match.group(0).split('"')[1]
            pane_decl_idx = modal_chunk.find(f'id="{pane_id}"')
            pane_snippet = modal_chunk[pane_decl_idx:pane_decl_idx+120]
            print(f"  ✅ Tab pane: {pane_id} -> {pane_snippet.replace(chr(10), ' ')}")
        else:
            print(f"  ❌ Tab pane for '{t}' NOT FOUND!")
