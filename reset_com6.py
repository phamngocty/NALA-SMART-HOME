import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')
print("Opening COM6...")
try:
    ser = serial.Serial('COM6', 115200, timeout=0.5)
    ser.setDTR(False)
    ser.setRTS(True)
    time.sleep(0.1)
    ser.setDTR(True)
    ser.setRTS(False)
    time.sleep(0.1)
    ser.setDTR(False)
    ser.setRTS(False)
    print("ESP32 Reset pulse sent on COM6. Reading boot logs (10s)...")
    start = time.time()
    while time.time() - start < 10:
        line = ser.readline()
        if line:
            try:
                print(line.decode('utf-8', errors='replace').rstrip())
            except Exception:
                pass
    ser.close()
    print("COM6 closed.")
except Exception as e:
    print(f"Error on COM6: {e}")
