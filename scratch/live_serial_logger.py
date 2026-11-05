import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200
log_file = 'scratch/touch_events.log'

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

print(f"=== LIVE SERIAL LOGGER RUNNING ON {port} ===")
with open(log_file, 'a', encoding='utf-8') as f_out:
    f_out.write(f"\n--- SESSION STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    f_out.flush()

try:
    while True:
        line = ser.readline()
        if line:
            try:
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    ts = time.strftime('%H:%M:%S')
                    with open(log_file, 'a', encoding='utf-8') as f_out:
                        f_out.write(f"[{ts}] {decoded}\n")
                        f_out.flush()
                    if any(tag in decoded for tag in ["[LVGL-INDEV]", "[UI-EVENT]", "[UI]", "Clicked", "TOUCH", "Alive"]):
                        print(f"[{ts}] {decoded}")
            except Exception:
                pass
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    print("=== LIVE SERIAL LOGGER STOPPED ===")
