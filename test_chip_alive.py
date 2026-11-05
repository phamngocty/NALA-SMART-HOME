import serial
import time

ser = serial.Serial('COM20', 115200, timeout=1)
ser.dtr = False
ser.rts = False
time.sleep(0.1)
# Send a newline
ser.write(b"\r\n")
print("Reading serial for 3 seconds...")
start = time.time()
while time.time() - start < 3:
    l = ser.readline()
    if l:
        print(l.decode('utf-8', errors='replace').rstrip())
ser.close()
