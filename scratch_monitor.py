import sys, serial, time, os

sys.stdout.reconfigure(encoding='utf-8')
log_file = os.path.join(os.path.dirname(__file__), 'live_serial.log')

print("Starting Live Serial Logger on COM20...")
with open(log_file, 'a', encoding='utf-8') as f:
    f.write(f"\n--- SESSION STARTED AT {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")

try:
    s = serial.Serial('COM20', 115200, timeout=0.2)
except Exception as e:
    print(f"Error opening COM20: {e}")
    sys.exit(1)

while True:
    try:
        line = s.readline()
        if line:
            decoded = line.decode('utf-8', errors='replace').rstrip()
            timestamp = time.strftime('%H:%M:%S')
            log_line = f"[{timestamp}] {decoded}"
            print(log_line, flush=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
    except Exception as e:
        time.sleep(0.1)
