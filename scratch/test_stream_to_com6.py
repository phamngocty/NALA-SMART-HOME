import sys, serial, time, websockets, asyncio, struct, math

sys.stdout.reconfigure(encoding='utf-8')

async def send_2s_stream():
    ser = serial.Serial('COM6', 115200, timeout=0.1)
    time.sleep(0.3)
    ser.reset_input_buffer()

    uri = 'ws://192.168.1.114:8765/ws/tester_intercom'
    print('Connecting to NAS WebSocket...')
    async with websockets.connect(uri) as ws:
        await ws.send('{"type": "register_admin"}')
        await asyncio.sleep(0.3)

        magic = 0xA55A
        sender_id = 1
        target_id = 2 # Panel 2
        
        # 16000 samples/s, 256 samples per packet = 62.5 packets per second
        # 120 packets = ~2 seconds
        pcm = [int(math.sin(2 * math.pi * (i % 16) / 16.0) * 24000) for i in range(256)]
        
        print('Sending 2-second 1kHz stream to Panel 2 (ID 2)...')
        for s in range(120):
            flag = 1 if s == 0 else (3 if s == 119 else 2)
            pkt = struct.pack('<HBBHB256hB', magic, sender_id, target_id, s, flag, *pcm, 0)
            await ws.send(pkt)
            await asyncio.sleep(0.016)

        print('Stream finished.')
        t0 = time.time()
        while time.time() - t0 < 1.5:
            if ser.in_waiting:
                print('[COM6]', ser.readline().decode('utf-8', errors='ignore').strip())
            await asyncio.sleep(0.01)

    ser.close()

asyncio.run(send_2s_stream())
