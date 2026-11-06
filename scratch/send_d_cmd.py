import serial
import time

try:
    with serial.Serial('COM6', 115200, timeout=1, write_timeout=1) as ser:
        ser.dtr = True
        ser.rts = False
        time.sleep(0.5)
        # Flush input buffer
        ser.reset_input_buffer()
        # Send 'd'
        ser.write(b'd\n')
        ser.flush()
        start = time.time()
        lines = []
        while time.time() - start < 3:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                lines.append(line)
        if lines:
            print("Received", len(lines), "lines:")
            for l in lines[:10]:
                print(l)
        else:
            print("No response from 'd' command.")
except Exception as e:
    print("Serial error:", e)
