import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000', timeout=10)
# Run fping or quick ping sweep
cmd = """
python3 -c "
import subprocess, concurrent.futures

def ping(ip):
    res = subprocess.run(['ping', '-c', '1', '-W', '1', ip], stdout=subprocess.DEVNULL)
    return ip, res.returncode == 0

ips = [f'192.168.1.{i}' for i in range(1, 255)]
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as ex:
    results = list(ex.map(ping, ips))

for ip, ok in results:
    if ok:
        print(f'ALIVE: {ip}')
"
ip neigh
"""
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode('utf-8', errors='replace'))
ssh.close()
