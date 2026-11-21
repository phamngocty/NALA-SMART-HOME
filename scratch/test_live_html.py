import requests

res = requests.get('http://192.168.1.114:8765/', timeout=5)
print('HTTP status:', res.status_code)
print('Contains memoryAliasesList:', 'memoryAliasesList' in res.text)
print('Contains memoryHabitsList:', 'memoryHabitsList' in res.text)
print('Contains memoryFactsList:', 'memoryFactsList' in res.text)
print('Contains xzVoiceTrigger:', 'xzVoiceTrigger' in res.text)
print('Contains tab_vp_test style block:', 'id="tab_vp_test" style="display: block;"' in res.text)
