import serial
import time

ser = serial.Serial('COM6', 115200, timeout=0.5)
ser.dtr = False
ser.rts = True
time.sleep(0.1)
ser.rts = False
time.sleep(0.1)
ser.dtr = True

start = time.time()
while time.time() - start < 5:
    line = ser.readline().decode('utf-8', errors='replace').strip()
    if line:
        print(line)

ser.close()
