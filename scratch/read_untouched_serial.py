import serial
import time

try:
    ser = serial.Serial('COM6', 115200, timeout=0.1)
    # DO NOT TOUCH DTR OR RTS
    start = time.time()
    received = False
    while time.time() - start < 4:
        data = ser.read(1024)
        if data:
            print(data.decode('utf-8', errors='replace'), end='')
            received = True
    ser.close()
    if not received:
        print("[No data received on COM6]")
except Exception as e:
    print("Serial error:", e)
