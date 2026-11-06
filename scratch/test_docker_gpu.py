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

# Enable nvidia-persistenced so the driver stays warm and socket exists
print("=== Starting nvidia-persistenced ===")
out, err = run_sudo("systemctl start nvidia-persistenced && systemctl enable nvidia-persistenced")
print("OUT:", out, "ERR:", err)

# Restart docker so runtime picks up the fresh nvidia driver
print("=== Restarting docker daemon ===")
out, err = run_sudo("systemctl restart docker")
print("OUT:", out, "ERR:", err)

# Test docker run with GPU
print("=== Testing docker run --gpus all ===")
out, err = run_sudo("docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi")
print("OUT:\n", out)
print("ERR:\n", err)

ssh.close()
