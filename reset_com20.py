import serial
import time

ser = serial.Serial('COM20', 115200, timeout=0.5)
# Pulse DTR to reset ESP32
ser.setDTR(False)
ser.setRTS(True)
time.sleep(0.1)
ser.setDTR(True)
ser.setRTS(False)
time.sleep(0.1)
ser.setDTR(False)
ser.setRTS(False)

print("ESP32 Reset pulse sent. Reading boot logs...")
start = time.time()
while time.time() - start < 6:
    line = ser.readline()
    if line:
        try:
            print(line.decode('utf-8', errors='replace').rstrip())
        except Exception:
            pass
ser.close()
