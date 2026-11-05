import serial
import time
import sys

port = 'COM20'
baud = 115200
log_file = 'scratch/touch_v314.log'

ser = serial.Serial()
ser.port = port
ser.baudrate = baud
ser.dtr = False
ser.rts = False

try:
    ser.open()
except Exception as e:
    sys.exit(0)

with open(log_file, 'a', encoding='utf-8') as f:
    f.write(f"\n--- MONITOR STARTED {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

try:
    while True:
        line = ser.readline()
        if line:
            try:
                dec = line.decode('utf-8', errors='replace').rstrip()
                if any(k in dec for k in ["[LVGL-INDEV]", "[UI-EVENT]", "[UI]", "[HA]", "[TOUCH]", "[SYSTEM]"]):
                    ts = time.strftime('%H:%M:%S')
                    msg = f"[{ts}] {dec}"
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(msg + '\n')
                        f.flush()
                    print(msg)
            except Exception:
                pass
except KeyboardInterrupt:
    pass
finally:
    ser.close()
