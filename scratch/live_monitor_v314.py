import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200
duration = 45

ser = serial.Serial()
ser.port = port
ser.baudrate = baud
ser.dtr = False
ser.rts = False

try:
    ser.open()
except Exception as e:
    print(f"Error opening {port}: {e}")
    sys.exit(1)

print(f"=== LIVE MONITOR v3.1.4 ACTIVE ON {port} ({duration}s) ===")
print("Screen is ready! Please touch the tabs at bottom and buttons...")

t_end = time.time() + duration
try:
    while time.time() < t_end:
        line = ser.readline()
        if line:
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if any(tag in decoded for tag in ["[LVGL-INDEV]", "[UI-EVENT]", "[UI]", "[HA]", "[TOUCH]", "[SYSTEM]", "[WS]", "Clicked"]):
                    print(f"[{time.strftime('%H:%M:%S')}] {decoded}")
                elif "Alive" in decoded:
                    print(f"[{time.strftime('%H:%M:%S')}] (heartbeat: {decoded})")
            except Exception:
                pass
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    print("=== LIVE MONITOR v3.1.4 ENDED ===")
