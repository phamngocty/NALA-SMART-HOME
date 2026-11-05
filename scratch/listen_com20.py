import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200
duration = 20

print(f"Connecting to {port} at {baud} baud (listening for {duration}s)...")
try:
    ser = serial.Serial(port, baud, timeout=0.5)
except Exception as e:
    print(f"Failed to open {port}: {e}")
    sys.exit(1)

start_time = time.time()
try:
    while time.time() - start_time < duration:
        line = ser.readline()
        if line:
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    print(decoded)
            except Exception:
                pass
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    print("Closed COM20 connection.")
