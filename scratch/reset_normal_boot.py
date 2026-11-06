import serial
import time

ser = serial.Serial('COM6', 115200, timeout=0.1)

# Normal boot: DTR=False (GPIO0=HIGH), pulse RTS (EN low then high)
ser.dtr = False
ser.rts = True
time.sleep(0.1)
ser.rts = False
time.sleep(0.1)
# Keep DTR=False!
ser.dtr = False

start = time.time()
while time.time() - start < 4:
    data = ser.read(1024)
    if data:
        print(data.decode('utf-8', errors='replace'), end='')

ser.close()
