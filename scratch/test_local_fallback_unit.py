import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

py_test = """
import asyncio
from app.ai_agent_router import AIAgentRouter
from app.ha_bridge import HABridge

async def test_fallback():
    ha = HABridge('ws://192.168.1.114:8123/api/websocket', 'dummy_token')
    # Mock states in ha
    ha.states = {
        'light.den_phong_khach': {'attributes': {'friendly_name': 'Đèn phòng khách'}},
        'climate.dieu_hoa_phong_ngu': {'attributes': {'friendly_name': 'Máy lạnh phòng ngủ'}}
    }
    async def mock_call(domain, service, entity_id, service_data=None):
        print(f'[MOCK HA] Called service {domain}.{service} on {entity_id} with {service_data}')
        return True
    ha.call_service = mock_call

    router = AIAgentRouter('', '', ha)
    router.config = {'active_provider': 'gemini', 'auto_fallback': True}

    res1 = await router._try_local_rule_fallback('Bật đèn phòng khách', 'Phòng Khách')
    print('Result 1 (Light turn_on):', res1)

    res2 = await router._try_local_rule_fallback('Tắt máy lạnh phòng ngủ', 'Phòng Ngủ')
    print('Result 2 (Climate off):', res2)

    res3 = await router._try_local_rule_fallback('Hôm nay trời thế nào?', 'Phòng Khách')
    print('Result 3 (Non-command):', res3)

asyncio.run(test_fallback())
"""

stdin, stdout, stderr = ssh.exec_command(f"python3 -c \"{py_test}\"", environment={'PYTHONPATH': '/home/nas152/nala-voice-intercom-system/server_nas_hub'})
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print("OUTPUT:\n", out)
if err:
    print("ERRORS:\n", err)

ssh.close()
