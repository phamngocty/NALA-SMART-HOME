import serial
import time

ser = serial.Serial('COM20', 115200, timeout=1)
print("Listening to COM20 for 4 seconds...")
start = time.time()
while time.time() - start < 4:
    line = ser.readline()
    if line:
        try:
            print(line.decode('utf-8', errors='replace').rstrip())
        except Exception:
            pass
ser.close()
