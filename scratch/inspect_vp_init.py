with open('server_nas_hub/app/voiceprint_manager.py', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('class VoiceprintManager')
print(content[:idx+1500])
