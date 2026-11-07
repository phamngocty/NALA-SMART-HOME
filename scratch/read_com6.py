import serial
import time

s = serial.Serial('COM6', 115200, timeout=2)
print("Listening to COM6 for 12 seconds...")
start = time.time()
while time.time() - start < 12:
    line = s.readline()
    if line:
        txt = line.decode('utf-8', errors='replace').strip()
        print(txt.encode('ascii', errors='replace').decode('ascii'))
s.close()
