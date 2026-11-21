import subprocess

res = subprocess.run(["git", "show", "HEAD~2:server_nas_hub/app/static/index.html"], capture_output=True, text=True, encoding="utf-8")
text = res.stdout
print("Total length HEAD~2:", len(text))

p = text.find('id="aiModal"')
if p != -1:
    print("Found aiModal in HEAD~2! Length around it:")
    p_end = text.find('<!--', p + 100)
    print(text[p:p+3000])
else:
    print("aiModal not found in HEAD~2, looking for aiConfig...")
    for target in ['id="tab_sys_ai"', 'id="aiCard"', 'AI & API']:
        idx = text.find(target)
        print(f"target {target}: {idx}")
