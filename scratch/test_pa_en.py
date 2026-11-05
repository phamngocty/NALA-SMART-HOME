import sys, serial, time
sys.stdout.reconfigure(encoding='utf-8')
ser = serial.Serial('COM6', 115200, timeout=1)
time.sleep(0.3)
print('Sending 0 (PA_EN = LOW)...')
ser.write(b'0\n')
time.sleep(1)
while ser.in_waiting:
    print(ser.readline().decode('utf-8', errors='ignore').strip())

print('Sending 1 (PA_EN = HIGH)...')
ser.write(b'1\n')
time.sleep(1)
while ser.in_waiting:
    print(ser.readline().decode('utf-8', errors='ignore').strip())

ser.close()
