import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

test_code = """
import sys
sys.path.insert(0, '/app')
import asyncio
from app.ai_agent_router import AIAgentRouter
from app.ha_bridge import HomeAssistantBridge

async def test_fallback():
    ha = HomeAssistantBridge('ws://192.168.1.114:8123/api/websocket', 'dummy_token')
    ha.states = {
        'light.den_phong_khach': {'attributes': {'friendly_name': 'Đèn phòng khách'}},
        'climate.dieu_hoa_phong_ngu': {'attributes': {'friendly_name': 'Máy lạnh phòng ngủ'}}
    }
    async def mock_call(domain, service, entity_id, service_data=None):
        print(f'[MOCK HA] Called {domain}.{service} on {entity_id} with {service_data}')
        return True
    ha.call_service = mock_call

    router = AIAgentRouter('', '', ha)
    res1 = await router._try_local_rule_fallback('Bật đèn phòng khách', 'Phòng Khách')
    print('Result 1 (Light):', res1)
    res2 = await router._try_local_rule_fallback('Tắt máy lạnh', 'Phòng Ngủ')
    print('Result 2 (Climate):', res2)

asyncio.run(test_fallback())
"""

sftp = ssh.open_sftp()
with sftp.file('/home/nas152/nala-voice-intercom-system/server_nas_hub/app/test_fb.py', 'w') as f:
    f.write(test_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("echo 271000 | sudo -S docker exec nala_nas_ws_hub python3 /app/app/test_fb.py")
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')
print("OUTPUT:\n", out)
if err:
    print("ERRORS:\n", err)

# Cleanup
ssh.exec_command("rm -f /home/nas152/nala-voice-intercom-system/server_nas_hub/app/test_fb.py")
ssh.close()
