import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.1.114', username='nas152', password='271000')

cmds = [
    'lspci -nnk | grep -iA3 nvidia',
    'cat /proc/driver/nvidia/version 2>&1',
    'modinfo nvidia | grep ^version 2>&1',
    'dpkg -l | grep -E "nvidia-driver|nvidia-utils|libnvidia|linux-modules-nvidia" | grep "^ii"',
    'lsmod | grep nvidia',
    'uname -r'
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
