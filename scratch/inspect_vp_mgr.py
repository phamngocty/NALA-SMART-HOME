with open('server_nas_hub/app/voiceprint_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("File size:", len(content))
idx = content.find('def enroll(')
print(content[idx:idx+3000])
