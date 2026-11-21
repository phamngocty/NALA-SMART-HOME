with open('server_nas_hub/app/static/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('var TARGET_VER = "v3.2.0";', 'var TARGET_VER = "v3.2.1";')
text = text.replace('var TARGET_VER = "v3.1.0";', 'var TARGET_VER = "v3.2.1";')

with open('server_nas_hub/app/static/index.html', 'w', encoding='utf-8') as f:
    f.write(text)

print("Bumped TARGET_VER to v3.2.1")
