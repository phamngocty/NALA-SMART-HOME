import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200

ser = serial.Serial()
ser.port = port
ser.baudrate = baud
ser.dtr = False
ser.rts = False
ser.open()

print("Connected to COM20 WITHOUT RESETTING ESP32.")
print("Reading lines for 10 seconds. DO NOT TOUCH THE SCREEN...")

t_end = time.time() + 10.0
while time.time() < t_end:
    line = ser.readline()
    if line:
        decoded = line.decode('utf-8', errors='replace').rstrip()
        if decoded:
            print(f"[{time.strftime('%H:%M:%S')}] {decoded}")

ser.close()
print("Done 10s idle test.")
