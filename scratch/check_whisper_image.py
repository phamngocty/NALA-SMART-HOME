import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    err = "\n".join([line for line in err.splitlines() if "Password:" not in line and "authenticate" not in line])
    return out, err

print("=== Checking if faster-whisper image exists on NAS ===")
out, err = run_sudo("docker images | grep -i whisper")
print("IMAGES:", out)

print("=== Checking port 8095 on NAS ===")
out, err = run_sudo("ss -tulpn | grep 8095")
print("PORT 8095:", out)

ssh.close()
