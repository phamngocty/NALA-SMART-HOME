import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200
duration = 60

print(f"=== LIVE TOUCH MONITOR STARTED ON {port} (Listening for {duration}s) ===")
print("Please touch the screen: Tap the bottom tabs, tap TOAN NHA, tap device buttons...")

try:
    ser = serial.Serial(port, baud, timeout=0.2)
except Exception as e:
    print(f"Error opening {port}: {e}")
    sys.exit(1)

start_time = time.time()
try:
    while time.time() - start_time < duration:
        line = ser.readline()
        if line:
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if any(k in decoded for k in ["[LVGL-INDEV]", "[UI-EVENT]", "[UI]", "[TOUCH]", "[WS]", "Clicked"]):
                    print(f"[{time.strftime('%H:%M:%S')}] {decoded}")
            except Exception:
                pass
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    print("=== MONITOR ENDED ===")
