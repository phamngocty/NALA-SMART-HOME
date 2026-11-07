import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')
s = paramiko.SSHClient()
s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
s.connect('192.168.1.114', username='nas152', password='271000')

cmd = 'find /home/nas152 -name "*devices*.json"'
_, out, _ = s.exec_command(cmd)
print('On host:', out.read().decode('utf-8', errors='ignore'))

cmd2 = 'docker exec nala_nas_ws_hub find / -name "*devices*.json" 2>/dev/null'
_, out2, _ = s.exec_command(cmd2)
print('In container:', out2.read().decode('utf-8', errors='ignore'))

# Also check docker inspect to see volume mounts or working dir
cmd3 = 'docker inspect nala_nas_ws_hub --format "{{.Config.WorkingDir}} | {{range .Mounts}}{{.Source}} -> {{.Destination}} {{end}}"'
_, out3, _ = s.exec_command(cmd3)
print('Docker inspect:', out3.read().decode('utf-8', errors='ignore'))

s.close()
