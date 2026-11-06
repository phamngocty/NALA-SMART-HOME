import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

def run_sudo(cmd):
    stdin, stdout, stderr = ssh.exec_command(f'echo 271000 | sudo -S {cmd}')
    return stdout.read().decode().strip(), stderr.read().decode().strip()

print("fuser:", run_sudo("fuser -v /dev/nvidia*"))
print("lsof:", run_sudo("lsof /dev/nvidia*"))
print("persistenced:", run_sudo("systemctl status nvidia-persistenced"))

ssh.close()
