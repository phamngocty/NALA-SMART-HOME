import serial
import time
import sys

sys.stdout.reconfigure(encoding='utf-8')

port = 'COM20'
baud = 115200

print(f"Connecting to {port} to probe FT6336 registers...")
ser = serial.Serial(port, baud, timeout=0.5)
time.sleep(0.5)

# Clear any pending buffer
ser.reset_input_buffer()

# Send command 'p'
ser.write(b'p\n')
print("Sent 'p' command, reading response for 3 seconds...")

t_end = time.time() + 3.0
while time.time() < t_end:
    line = ser.readline()
    if line:
        decoded = line.decode('utf-8', errors='replace').rstrip()
        if decoded:
            print(decoded)

ser.close()
print("Done.")
