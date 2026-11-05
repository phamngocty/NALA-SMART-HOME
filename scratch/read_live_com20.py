import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

ser = serial.Serial('COM20', 115200, timeout=1)
time.sleep(1)

# Drain
while ser.in_waiting:
    ser.readline()

print("Sending 't' to trigger speaker test...")
ser.write(b"t\n")
ser.flush()

start = time.time()
while time.time() - start < 4:
    if ser.in_waiting:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print("[ESP32]", line)
    time.sleep(0.02)

ser.close()
