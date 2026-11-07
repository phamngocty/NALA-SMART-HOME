import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

commands = [
    ('CPU', 'lscpu | grep -E "Model name|CPU\(s\):"'),
    ('RAM', 'free -h'),
    ('GPU', 'nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader || echo "No Nvidia GPU"'),
    ('DISK', 'df -h / | tail -n 1'),
    ('DOCKER_AI', 'docker ps --filter "name=nala" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"')
]

for name, cmd in commands:
    print(f"=== {name} ===")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore').strip()
    print(out)

ssh.close()
