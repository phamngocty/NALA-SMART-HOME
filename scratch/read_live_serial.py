import serial
import time

ser = serial.Serial('COM6', 115200, timeout=0.2)
ser.dtr = True
ser.rts = False

start = time.time()
while time.time() - start < 6:
    line = ser.readline().decode('utf-8', errors='replace').strip()
    if line:
        print(line)

ser.close()
