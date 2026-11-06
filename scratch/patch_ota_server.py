with open('server_nas_hub/app/main_ws_server.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''@app.get("/api/ota/firmware/{filename}")
async def download_firmware(filename: str):
    """Endpoint để ESP32-S3 tải stream file firmware binary qua HTTP GET."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(FIRMWARE_DIR, safe_name)
    if not os.path.exists(file_path):
        return JSONResponse({"status": "error", "message": "Firmware file not found"}, status_code=404)
    return FileResponse(file_path, media_type="application/octet-stream", filename=safe_name)

@app.post("/api/ota/start")
async def start_ota_update(req: OTAStartRequest, request: Request):
    """Phát lệnh kích hoạt OTA qua WebSocket tới 1 hoặc toàn bộ màn hình."""
    meta_path = os.path.join(FIRMWARE_DIR, "ota_meta.json")
    if not os.path.exists(meta_path):
        return JSONResponse({"status": "error", "message": "Chưa có bản firmware nào được tải lên NAS Hub"}, status_code=400)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    host = request.headers.get("host", f"192.168.1.114:{PORT}")
    if "localhost" in host or "127.0.0.1" in host:
        host = f"192.168.1.114:{PORT}"

    filename = req.firmware_filename or "firmware_latest.bin"
    firmware_url = f"http://{host}/api/ota/firmware/{filename}"

    ota_msg = {
        "type": "ota_start",
        "url": firmware_url,
        "size": meta.get("size_bytes", 0),
        "md5": meta.get("md5", ""),
        "version": meta.get("version", "v2.5.0")
    }

    target_code = req.target.strip()
    sent_count = 0

    if target_code.lower() == "all":
        for code, ws in list(active_sockets.items()):
            if not code.startswith("web_admin") and code != "default_panel":
                try:
                    await ws.send_json(ota_msg)
                    sent_count += 1
                    logger.info("Sent OTA command to Panel [%s]", code)
                except Exception as e:
                    logger.error("Failed to send OTA command to [%s]: %s", code, e)
    else:
        target_ws = active_sockets.get(target_code.upper())
        if not target_ws:
            dev = devices_db.get(target_code.upper())
            if dev:
                target_ws = active_sockets.get(dev.get("device_id")) or active_sockets.get(dev.get("mac"))
        if target_ws:
            try:
                await target_ws.send_json(ota_msg)
                sent_count = 1
                logger.info("Sent OTA command to Panel [%s]", target_code)
            except Exception as e:
                return JSONResponse({"status": "error", "message": f"Không thể gửi lệnh OTA tới thiết bị: {e}"}, status_code=500)
        else:
            return JSONResponse({"status": "error", "message": f"Thiết bị [{target_code}] hiện đang offline"}, status_code=400)

    await broadcast_to_admins({
        "type": "ota_started",
        "target": target_code,
        "sent_count": sent_count,
        "version": meta.get("version"),
        "url": firmware_url
    })'''

replacement = '''@app.get("/api/ota/firmware/{filename}")
async def download_firmware(filename: str, request: Request, code: Optional[str] = None):
    """Endpoint để ESP32-S3 tải stream file firmware binary qua HTTP GET, đồng thời phát sóng tiến độ theo thời gian thực tới Web Admin."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(FIRMWARE_DIR, safe_name)
    if not os.path.exists(file_path):
        return JSONResponse({"status": "error", "message": "Firmware file not found"}, status_code=404)

    file_size = os.path.getsize(file_path)

    # Nếu không có query param code, tự động tìm code dựa theo client IP
    if not code:
        client_ip = request.client.host if request.client else ""
        for c, dev in devices_db.items():
            if dev.get("ip") == client_ip:
                code = c
                break

    target_code = code.upper() if code else ""
    logger.info("ESP32 [%s] bắt đầu tải OTA firmware: %s (%d bytes)", target_code or "Unknown", safe_name, file_size)

    async def file_sender():
        sent_bytes = 0
        last_pct = -1
        last_time = time.time()

        if target_code:
            await broadcast_to_admins({
                "type": "ota_progress",
                "pairing_code": target_code,
                "progress": 1,
                "status": "downloading",
                "message": "Thiết bị đã kết nối, bắt đầu truyền dữ liệu firmware..."
            })

        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(32768)  # 32KB
                if not chunk:
                    break
                sent_bytes += len(chunk)
                pct = int((sent_bytes * 100) / file_size) if file_size > 0 else 50
                if pct > 99:
                    pct = 99

                now = time.time()
                if (pct >= last_pct + 2 or now - last_time >= 0.4) and target_code:
                    last_pct = pct
                    last_time = now
                    await broadcast_to_admins({
                        "type": "ota_progress",
                        "pairing_code": target_code,
                        "progress": pct,
                        "status": "downloading",
                        "message": f"Đang truyền nạp: {pct}% ({round(sent_bytes / 1024)} KB / {round(file_size / 1024)} KB)"
                    })

                yield chunk
                await asyncio.sleep(0.001)

        if target_code:
            await broadcast_to_admins({
                "type": "ota_progress",
                "pairing_code": target_code,
                "progress": 100,
                "status": "flashing",
                "message": "Đã truyền đủ 100% file! Màn hình đang ghi Flash và khởi động lại..."
            })

    headers = {
        "Content-Length": str(file_size),
        "Content-Disposition": f'attachment; filename="{safe_name}"',
        "Accept-Ranges": "bytes"
    }
    return StreamingResponse(file_sender(), media_type="application/octet-stream", headers=headers)

@app.post("/api/ota/start")
async def start_ota_update(req: OTAStartRequest, request: Request):
    """Phát lệnh kích hoạt OTA qua WebSocket tới 1 hoặc toàn bộ màn hình."""
    meta_path = os.path.join(FIRMWARE_DIR, "ota_meta.json")
    if not os.path.exists(meta_path):
        return JSONResponse({"status": "error", "message": "Chưa có bản firmware nào được tải lên NAS Hub"}, status_code=400)

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    host = request.headers.get("host", f"192.168.1.114:{PORT}")
    if "localhost" in host or "127.0.0.1" in host:
        host = f"192.168.1.114:{PORT}"

    filename = req.firmware_filename or "firmware_latest.bin"
    target_code = req.target.strip()
    sent_count = 0

    if target_code.lower() == "all":
        for code, ws in list(active_sockets.items()):
            if not code.startswith("web_admin") and code != "default_panel":
                try:
                    ota_msg = {
                        "type": "ota_start",
                        "url": f"http://{host}/api/ota/firmware/{filename}?code={code}",
                        "size": meta.get("size_bytes", 0),
                        "md5": meta.get("md5", ""),
                        "version": meta.get("version", "v2.5.0")
                    }
                    await ws.send_json(ota_msg)
                    sent_count += 1
                    logger.info("Sent OTA command to Panel [%s]", code)
                except Exception as e:
                    logger.error("Failed to send OTA command to [%s]: %s", code, e)
    else:
        target_ws = active_sockets.get(target_code.upper())
        if not target_ws:
            dev = devices_db.get(target_code.upper())
            if dev:
                target_ws = active_sockets.get(dev.get("device_id")) or active_sockets.get(dev.get("mac"))
        if target_ws:
            try:
                firmware_url = f"http://{host}/api/ota/firmware/{filename}?code={target_code.upper()}"
                ota_msg = {
                    "type": "ota_start",
                    "url": firmware_url,
                    "size": meta.get("size_bytes", 0),
                    "md5": meta.get("md5", ""),
                    "version": meta.get("version", "v2.5.0")
                }
                await target_ws.send_json(ota_msg)
                sent_count = 1
                logger.info("Sent OTA command to Panel [%s]", target_code)
            except Exception as e:
                return JSONResponse({"status": "error", "message": f"Không thể gửi lệnh OTA tới thiết bị: {e}"}, status_code=500)
        else:
            return JSONResponse({"status": "error", "message": f"Thiết bị [{target_code}] hiện đang offline"}, status_code=400)

    await broadcast_to_admins({
        "type": "ota_started",
        "target": target_code,
        "sent_count": sent_count,
        "version": meta.get("version"),
        "url": f"http://{host}/api/ota/firmware/{filename}"
    })'''

text_norm = text.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
replacement_norm = replacement.replace('\r\n', '\n')

if target_norm in text_norm:
    new_text = text_norm.replace(target_norm, replacement_norm)
    with open('server_nas_hub/app/main_ws_server.py', 'w', encoding='utf-8', newline='\r\n') as f:
        f.write(new_text)
    print("SUCCESS: Updated main_ws_server.py")
else:
    print("ERROR: Target not found in main_ws_server.py")
