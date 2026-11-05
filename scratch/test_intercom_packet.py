import sys, serial, time, websockets, asyncio, struct, math

sys.stdout.reconfigure(encoding='utf-8')

async def test_send():
    ser = serial.Serial('COM6', 115200, timeout=0.1)
    time.sleep(0.5)
    ser.reset_input_buffer()

    uri = 'ws://192.168.1.114:8765/ws/web_admin_tester'
    print('Connecting to NAS WebSocket...')
    async with websockets.connect(uri) as ws:
        await ws.send('{"type": "register_admin"}')
        await asyncio.sleep(0.5)

        magic = 0xA55A
        sender_id = 1
        target_id = 2 # Panel 2
        seq = 1
        flag = 1 # START
        pcm = [int(math.sin(2 * math.pi * (i % 16) / 16.0) * 22000) for i in range(256)]
        
        pkt = struct.pack('<HBBHB256hB', magic, sender_id, target_id, seq, flag, *pcm, 0)
        print('Sending START packet to Panel 2 (ID 2)...')
        await ws.send(pkt)
        
        for s in range(2, 40):
            flag = 2 # DATA
            pkt = struct.pack('<HBBHB256hB', magic, sender_id, target_id, s, flag, *pcm, 0)
            await ws.send(pkt)
            await asyncio.sleep(0.016)

        flag = 3 # END
        pkt = struct.pack('<HBBHB256hB', magic, sender_id, target_id, 40, flag, *pcm, 0)
        await ws.send(pkt)
        print('Sent END packet.')

        t0 = time.time()
        while time.time() - t0 < 3:
            if ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print('[COM6]', line)
            await asyncio.sleep(0.01)

    ser.close()

asyncio.run(test_send())
