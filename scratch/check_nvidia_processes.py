import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmds = [
    'lsof /dev/nvidia* 2>&1',
    'fuser -v /dev/nvidia* 2>&1',
    'systemctl status nvidia-persistenced 2>&1',
    'sudo -n modprobe -r nvidia_uvm nvidia_drm nvidia_modeset nvidia 2>&1'
]

for c in cmds:
    print('==============================')
    print('CMD:', c)
    stdin, stdout, stderr = ssh.exec_command(c)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out)
    if err:
        print('ERR:', err)

ssh.close()
