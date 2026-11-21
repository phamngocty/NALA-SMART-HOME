with open('server_nas_hub/app/static/index.html.bak_v306', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('id="aiConfigModal"')
box_start = text.find('<div class="modal-box"', start)
# The end of modal is the matching closing </div> before <!-- Modal Trí Nhớ
next_modal = text.find('id="nalaMemoryModal"')
overlay_end = text.rfind('</div>', 0, next_modal)
# let's find the closing of modal-box
print(f"box_start: {box_start}, next_modal: {next_modal}")
chunk = text[box_start:overlay_end]
print(f"Chunk length: {len(chunk)}")
print("Chunk starts with:", chunk[:100])
print("Chunk ends with:", chunk[-100:])
