import urllib.request
import json

def test(prov, key):
    try:
        data = json.dumps({'provider': prov, 'api_key': key}).encode('utf-8')
        req = urllib.request.Request('http://192.168.1.114:8765/api/ai/models', data=data, headers={'Content-Type': 'application/json'})
        res = urllib.request.urlopen(req)
        body = json.loads(res.read().decode('utf-8'))
        print(f"{prov} (key={key!r}): status={body.get('status')}, count={len(body.get('models', []))}")
    except Exception as e:
        print(f"{prov} (key={key!r}): EXCEPTION {e}")

test('gemini', '')
test('gemini', 'AIzaFakeKey123')
test('groq', '')
test('groq', 'gsk_fake')
test('deepseek', '')
test('deepseek', 'sk-fake')
test('openrouter', '')
test('openrouter', 'sk-or-fake')
