import serial
import time

try:
    with serial.Serial('COM6', 115200, timeout=1, write_timeout=1) as ser:
        ser.dtr = True
        ser.rts = False
        time.sleep(0.2)
        # Send a newline or test command
        ser.write(b'\r\n')
        ser.flush()
        start = time.time()
        while time.time() - start < 3:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(line)
except Exception as e:
    print("Error:", e)
