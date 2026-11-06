import serial
import time

ser = serial.Serial('COM6', 115200, timeout=0.1)
# Toggle reset
ser.dtr = False
ser.rts = True
time.sleep(0.1)
ser.rts = False
time.sleep(0.05)
ser.dtr = True

start = time.time()
while time.time() - start < 3:
    data = ser.read(1024)
    if data:
        print(data.decode('utf-8', errors='replace'), end='')

ser.close()
