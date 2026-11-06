import sys
import paramiko

# Force UTF-8 output on Windows console
sys.stdout.reconfigure(encoding='utf-8')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    # Filter out sudo prompt from err
    err = "\n".join([line for line in err.splitlines() if "Password:" not in line and "authenticate" not in line])
    return out, err

print("=== Unloading old nvidia kernel modules (595.91) ===")
out, err = run_sudo("modprobe -r nvidia_uvm nvidia_drm nvidia_modeset nvidia")
print("OUT:", out)
print("ERR:", err)

print("=== Loading new nvidia kernel modules (595.99) ===")
out, err = run_sudo("modprobe nvidia")
print("OUT:", out)
print("ERR:", err)

print("=== Testing nvidia-smi ===")
out, err = run_sudo("nvidia-smi")
print("OUT:\n", out)
print("ERR:\n", err)

ssh.close()
