import urllib.request

try:
    resp = urllib.request.urlopen('http://192.168.1.114:8765/', timeout=5)
    print('Status:', resp.status)
    html = resp.read().decode('utf-8', errors='ignore')
    print('HTML Length:', len(html))
    print('Has Voiceprint Modal:', 'id="voiceprintModal"' in html)
    print('Has AI Config Modal:', 'id="aiConfigModal"' in html)
    print('Has btn-voiceprint-header:', 'btn-voiceprint-header' in html)
    print('Has openVoiceprintModal:', 'openVoiceprintModal' in html)
    print('Has fetchModelsForProvider:', 'fetchModelsForProvider' in html)
    print('Has loadAutomationRules:', 'loadAutomationRules' in html)
except Exception as e:
    print('Error:', e)
