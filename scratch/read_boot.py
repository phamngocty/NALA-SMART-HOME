import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')
# Open WITHOUT toggling DTR or RTS
s = serial.Serial('COM20', 115200, timeout=0.1, rtscts=False, dsrdtr=False)
s.dtr = False
s.rts = False

t0 = time.time()
while time.time() - t0 < 8:
    data = s.read(1024)
    if data:
        print(data.decode('utf-8', errors='replace'), end='', flush=True)
s.close()

