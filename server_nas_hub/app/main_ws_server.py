"""
NALA SMART HOME - CENTRAL WEBSOCKET SERVER & WEB MANAGEMENT HUB
Handles WebSocket connections from ESP32-S3 Wall Panels and ESP32-C3 Nodes.
Coordinates Device Pairing, Web Management Hub, HA Bridge, Audio Pipeline, and Intercom.
"""

import os
import json
import asyncio
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Monkey-patch uvicorn WebSocketsSansIOProtocol to decode UTF-8 with errors='replace'
# Prevents disconnects when ESP32 sends truncated UTF-8 in room names
try:
    from uvicorn.protocols.websockets.websockets_sansio_impl import WebSocketsSansIOProtocol
    def _safe_send_receive_event_to_app(self) -> None:
        data = self.frames[0] if len(self.frames) == 1 else b"".join(self.frames)
        self.frames = []
        if self.close_sent:
            return
        if self.curr_msg_data_type == "text":
            text = data.decode("utf-8", errors="replace")
            self.queue.put_nowait({"type": "websocket.receive", "text": text})
        else:
            self.queue.put_nowait({"type": "websocket.receive", "bytes": data})
        if not self.read_paused:
            self.read_paused = True
            self.transport.pause_reading()
    WebSocketsSansIOProtocol.send_receive_event_to_app = _safe_send_receive_event_to_app
    logger_init = logging.getLogger("MainWSServer")
    logger_init.info("Patched WebSocketsSansIOProtocol for resilient UTF-8 decoding!")
except Exception as patch_err:
    pass

from app.ha_bridge import HomeAssistantBridge
from app.intercom_router import IntercomRouter
from app.stt_tts_pipeline import AudioPipeline
from app.ai_agent_router import AIAgentRouter
from app.history_manager import HistoryManager

for env_candidate in [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
    os.path.join(os.path.dirname(__file__), ".env"),
    "/app/.env"
]:
    if os.path.exists(env_candidate):
        load_dotenv(env_candidate)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("MainWSServer")

# Configuration
PORT = int(os.getenv("PORT", 8765))
HA_WS_URL = os.getenv("HA_WS_URL", "ws://192.168.1.5:8123/api/websocket")
HA_TOKEN = os.getenv("HA_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
STT_URL = os.getenv("STT_SERVICE_URL", "http://localhost:8000/v1/audio/transcriptions")
TTS_URL = os.getenv("TTS_SERVICE_URL", "http://localhost:5000/api/tts")

app = FastAPI(title="NALA Central WebSocket & Web Management Hub")

# Ensure static directory exists and mount static files
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Firmware OTA Storage Directory
FIRMWARE_DIR = os.path.join(os.path.dirname(__file__), "firmware")
os.makedirs(FIRMWARE_DIR, exist_ok=True)

# Subsystems
ha_bridge = HomeAssistantBridge(HA_WS_URL, HA_TOKEN)
intercom = IntercomRouter()
audio_pipeline = AudioPipeline(STT_URL, TTS_URL)
ai_router = AIAgentRouter(GEMINI_API_KEY, DEEPSEEK_API_KEY, ha_bridge)
history_mgr = HistoryManager()

def get_buttons_with_state(dev: dict) -> list:
    """Đính kèm trạng thái thực tế (state, is_on, domain) từ Home Assistant vào các nút bấm."""
    buttons_with_state = []
    for b in dev.get("buttons", []):
        b_copy = dict(b)
        eid = b.get("entity_id", "")
        if eid:
            cur_state = ha_bridge.states.get(eid, {}).get("state", "off")
            b_copy["state"] = cur_state
            b_copy["is_on"] = (cur_state == "on" or (cur_state not in ["off", "unavailable", "unknown"]))
            if not b_copy.get("domain"):
                b_copy["domain"] = eid.split(".")[0] if "." in eid else "light"
        else:
            b_copy["state"] = "off"
            b_copy["is_on"] = False
        buttons_with_state.append(b_copy)
    return buttons_with_state

# Device Database Persistence
DEVICES_FILE = os.path.join(os.path.dirname(__file__), "devices.json")
devices_db: Dict[str, dict] = {}

def load_devices():
    global devices_db
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, "r", encoding="utf-8") as f:
                devices_db = json.load(f)
                logger.info("Loaded %d devices from %s", len(devices_db), DEVICES_FILE)
                # Đảm bảo mỗi device có intercom_id và đăng ký metadata vào intercom
                for code, dev in devices_db.items():
                    if "intercom_id" not in dev:
                        dev["intercom_id"] = intercom.assign_id(code)
                    else:
                        intercom.assign_id(code, dev["intercom_id"])
                    intercom.device_meta[code] = {
                        "room_name": dev.get("room_name", f"Panel {code}"),
                        "floor": dev.get("floor", "")
                    }
        except Exception as e:
            logger.error("Error loading devices file: %s", e)
            devices_db = {}

def save_devices():
    try:
        with open(DEVICES_FILE, "w", encoding="utf-8") as f:
            json.dump(devices_db, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Error saving devices file: %s", e)

# Active WebSocket connections: identifier -> WebSocket
active_sockets: Dict[str, WebSocket] = {}
# Device PCM recording buffers: device_id -> bytearray
audio_record_buffers: Dict[str, bytearray] = {}
intercom_audio_buffers: Dict[str, bytearray] = {}

def get_devices_list() -> List[dict]:
    """Cập nhật trạng thái online theo active_sockets và trả về danh sách thiết bị kèm Intercom ID."""
    for code, dev in devices_db.items():
        dev["online"] = dev.get("device_id") in active_sockets or code in active_sockets
        if "intercom_id" not in dev:
            dev["intercom_id"] = intercom.get_id(code) or intercom.assign_id(code)
    return list(devices_db.values())

async def broadcast_to_admins(msg: dict):
    """Gửi thông điệp thời gian thực tới tất cả Web Admin Dashboard đang mở."""
    for dev_id, ws in list(active_sockets.items()):
        if dev_id.startswith("web_admin"):
            try:
                await ws.send_json(msg)
            except Exception:
                pass

async def on_ha_state_change(entity_id: str, new_state: str, raw_obj: dict):
    """Khi có thiết bị trong Home Assistant thay đổi trạng thái, broadcast xuống tất cả Panel & Web Admin."""
    msg = {
        "type": "ha_state_change",
        "payload": {
            "entity_id": entity_id,
            "state": new_state
        }
    }
    for dev_id, ws in list(active_sockets.items()):
        try:
            await ws.send_json(msg)
        except Exception:
            pass

async def history_cleanup_task():
    while True:
        try:
            await asyncio.sleep(3600) # Mỗi 1 giờ kiểm tra dọn dẹp lịch sử theo lịch
            history_mgr.cleanup()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in history cleanup task: %s", e)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting NALA Central Hub on port %d...", PORT)
    load_devices()
    ha_bridge.add_state_listener(on_ha_state_change)
    asyncio.create_task(ha_bridge.connect())
    asyncio.create_task(history_cleanup_task())

# -----------------------------------------------------------------------------
# WEB MANAGEMENT HUB & REST APIS
# -----------------------------------------------------------------------------
@app.get("/")
@app.get("/admin")
async def get_admin_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "NALA Hub Running", "port": PORT})

@app.get("/api/devices")
async def get_devices():
    return JSONResponse(get_devices_list())

@app.get("/api/system/status")
async def get_system_status():
    devices = get_devices_list()
    return JSONResponse({
        "nas_hub": {"status": "online", "port": PORT},
        "ha_connected": ha_bridge.authenticated,
        "ha_url": ha_bridge.ws_url,
        "devices_total": len(devices),
        "devices_online": sum(1 for d in devices if d.get("online")),
        "devices_paired": sum(1 for d in devices if d.get("is_paired")),
        "active_sockets": len(active_sockets)
    })

class ButtonConfig(BaseModel):
    id: Optional[str] = None
    name: str
    entity_id: str
    icon: Optional[str] = "light"
    domain: Optional[str] = None

class PairRequest(BaseModel):
    pairing_code: str
    room_name: str
    floor: str
    buttons: Optional[List[ButtonConfig]] = None
    entities: Optional[List[str]] = None
    settings: Optional[dict] = None

@app.post("/api/devices/pair")
async def pair_device(req: PairRequest):
    code = req.pairing_code.upper()
    dev = devices_db.get(code)

    # Process custom buttons
    buttons_list = []
    if req.buttons is not None:
        buttons_list = [b.dict() for b in req.buttons]
    elif req.entities is not None:
        for idx, eid in enumerate(req.entities):
            domain = eid.split(".")[0]
            buttons_list.append({
                "id": f"btn_{idx+1}",
                "name": eid.split(".")[1].replace("_", " ").title(),
                "entity_id": eid,
                "icon": domain,
                "domain": domain
            })

    entities_list = [b["entity_id"] for b in buttons_list] if buttons_list else (req.entities or [])

    if not dev:
        dev = {
            "device_id": f"panel_{code.lower()}",
            "mac": "Unknown",
            "pairing_code": code,
            "ip": "Unknown",
            "model": "ES3C28P",
            "room_name": req.room_name,
            "floor": req.floor,
            "buttons": buttons_list,
            "entities": entities_list,
            "settings": req.settings or {"brightness": 90, "volume": 80, "ai_model": "gemini"},
            "is_paired": True,
            "online": True
        }
        devices_db[code] = dev
    else:
        dev["room_name"] = req.room_name
        dev["floor"] = req.floor
        if req.buttons is not None or req.entities is not None:
            dev["buttons"] = buttons_list
            dev["entities"] = entities_list
        if req.settings is not None:
            dev["settings"] = req.settings
        dev["is_paired"] = True

    if "intercom_id" not in dev:
        dev["intercom_id"] = intercom.assign_id(code)
    intercom.device_meta[code] = {
        "room_name": req.room_name,
        "floor": req.floor
    }

    save_devices()
    logger.info("Device [%s] paired: Room='%s', Floor='%s', Buttons=%d, Intercom_ID=%d", code, req.room_name, req.floor, len(dev.get("buttons", [])), dev.get("intercom_id", 1))

    # Gửi lệnh config_sync xuống Panel qua WebSocket ngay lập tức
    sync_msg = {
        "type": "config_sync",
        "payload": {
            "room": f"{req.room_name} - {req.floor}",
            "floor": req.floor,
            "my_intercom_id": dev.get("intercom_id", 1),
            "intercom_targets": intercom.get_targets(exclude_device_key=code),
            "buttons": get_buttons_with_state(dev),
            "entities": dev.get("entities", []),
            "settings": dev.get("settings", {})
        }
    }
    target_socket = active_sockets.get(code) or active_sockets.get(dev.get("device_id"))
    if target_socket:
        try:
            await target_socket.send_json(sync_msg)
            logger.info("Pushed config_sync to active panel WebSocket: %s", code)
        except Exception as e:
            logger.error("Failed to push config_sync to %s: %s", code, e)

    # Đồng bộ danh sách kênh Intercom mới tới các màn hình khác
    for code_k, ws_k in list(active_sockets.items()):
        if not code_k.startswith("web_admin") and code_k != code and code_k != "default_panel":
            try:
                await ws_k.send_json({
                    "type": "intercom_sync",
                    "payload": {
                        "my_intercom_id": devices_db.get(code_k, {}).get("intercom_id", 1),
                        "targets": intercom.get_targets(exclude_device_key=code_k)
                    }
                })
            except Exception:
                pass

    # Thông báo cập nhật tức thời tới các Web Dashboard
    await broadcast_to_admins({
        "type": "devices_update",
        "devices": get_devices_list(),
        "intercom_targets": intercom.get_targets()
    })

    return JSONResponse({"status": "success", "device": dev})

class UnpairRequest(BaseModel):
    pairing_code: str

@app.post("/api/devices/unpair")
async def unpair_device(req: UnpairRequest):
    code = req.pairing_code.upper()
    dev = devices_db.get(code)
    if dev:
        dev["is_paired"] = False
        save_devices()
        logger.info("Device [%s] unpaired (reset to discovered mode)", code)
        await broadcast_to_admins({
            "type": "devices_update",
            "devices": get_devices_list()
        })
        return JSONResponse({"status": "success", "message": f"Unpaired {code}"})
    return JSONResponse({"status": "error", "message": "Device not found"}, status_code=404)

class DeviceActionRequest(BaseModel):
    pairing_code: str
    action: str # "sync", "reboot", "ping"

@app.post("/api/devices/action")
async def handle_device_action(req: DeviceActionRequest):
    code = req.pairing_code.upper()
    dev = devices_db.get(code)
    if not dev:
        return JSONResponse({"status": "error", "message": "Device not found"}, status_code=404)

    target_socket = active_sockets.get(code) or active_sockets.get(dev.get("device_id"))
    if not target_socket:
        return JSONResponse({"status": "error", "message": "Device offline"}, status_code=400)

    if req.action == "sync":
        sync_msg = {
            "type": "config_sync",
            "payload": {
                "room": f"{dev.get('room_name', 'Phong Khach')} - {dev.get('floor', 'Tang Tret')}",
                "floor": dev.get('floor', 'Tang Tret'),
                "buttons": get_buttons_with_state(dev),
                "entities": dev.get("entities", []),
                "settings": dev.get("settings", {})
            }
        }
        await target_socket.send_json(sync_msg)
        logger.info("Manual config_sync triggered for [%s]", code)
        return JSONResponse({"status": "success", "message": f"Synced config to [{code}]"})
    elif req.action == "reboot":
        await target_socket.send_json({"type": "command", "action": "reboot"})
        logger.info("Reboot command sent to [%s]", code)
        return JSONResponse({"status": "success", "message": f"Sent reboot to [{code}]"})
    elif req.action in ("enter_ap", "reset_wifi"):
        await target_socket.send_json({"type": "enter_ap"})
        logger.info("Sent enter_ap command to [%s]", code)
        return JSONResponse({"status": "success", "message": f"Sent enter_ap to [{code}]"})

    return JSONResponse({"status": "success"})

@app.get("/api/ha/entities")
async def get_ha_entities():
    return JSONResponse(ha_bridge.get_entities_list())

class CallServiceRequest(BaseModel):
    domain: Optional[str] = "light"
    service: Optional[str] = "toggle"
    entity_id: str

@app.post("/api/ha/call_service")
async def call_ha_service(req: CallServiceRequest):
    domain = req.domain or req.entity_id.split(".")[0]
    success = await ha_bridge.call_service(domain, req.service, req.entity_id)
    return JSONResponse({"status": "success" if success else "failed"})

@app.get("/api/ha/areas")
async def get_ha_areas():
    return JSONResponse({
        "areas": ha_bridge.get_areas_list(),
        "floors": ha_bridge.get_floors_list()
    })

class HAConfigRequest(BaseModel):
    ha_ws_url: str
    ha_token: str

@app.get("/api/ha/config")
async def get_ha_config():
    token_preview = ""
    if ha_bridge.token:
        token_preview = ha_bridge.token[:8] + "..." + ha_bridge.token[-6:] if len(ha_bridge.token) > 14 else "******"
    return JSONResponse({
        "ha_ws_url": ha_bridge.ws_url,
        "ha_token_preview": token_preview,
        "authenticated": ha_bridge.authenticated,
        "areas_count": len(ha_bridge.areas),
        "floors_count": len(ha_bridge.floors),
        "entities_count": len(ha_bridge.states)
    })

@app.post("/api/ha/config")
async def update_ha_config(req: HAConfigRequest):
    global HA_WS_URL, HA_TOKEN
    HA_WS_URL = req.ha_ws_url.strip()
    HA_TOKEN = req.ha_token.strip()
    os.environ["HA_WS_URL"] = HA_WS_URL
    os.environ["HA_TOKEN"] = HA_TOKEN

    for env_path in [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "/app/.env",
        os.path.join(os.path.dirname(__file__), ".env")
    ]:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                found_url, found_token = False, False
                for line in lines:
                    if line.startswith("HA_WS_URL="):
                        new_lines.append(f"HA_WS_URL={HA_WS_URL}\n")
                        found_url = True
                    elif line.startswith("HA_TOKEN="):
                        new_lines.append(f"HA_TOKEN={HA_TOKEN}\n")
                        found_token = True
                    else:
                        new_lines.append(line)
                if not found_url: new_lines.append(f"HA_WS_URL={HA_WS_URL}\n")
                if not found_token: new_lines.append(f"HA_TOKEN={HA_TOKEN}\n")
                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                logger.info("Updated .env file at %s with new HA configuration.", env_path)
            except Exception as e:
                logger.error("Failed to write .env file at %s: %s", env_path, e)

    await ha_bridge.reconfigure(HA_WS_URL, HA_TOKEN)
    await broadcast_to_admins({
        "type": "ha_config_updated",
        "system": {
            "ha_connected": ha_bridge.authenticated,
            "ha_url": ha_bridge.ws_url
        }
    })
    return JSONResponse({"status": "success", "message": "Updated Home Assistant configuration"})

@app.post("/api/ha/test_connection")
async def test_ha_connection(req: HAConfigRequest):
    url = req.ha_ws_url.strip()
    token = req.ha_token.strip()
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(url, timeout=aiohttp.ClientTimeout(total=5)) as ws:
                msg = await ws.receive_json()
                await ws.send_json({"type": "auth", "access_token": token})
                auth_res = await ws.receive_json()
                if auth_res.get("type") == "auth_ok":
                    await ws.send_json({"id": 1, "type": "config/area_registry/list"})
                    areas = (await ws.receive_json()).get("result", [])
                    await ws.send_json({"id": 2, "type": "config/floor_registry/list"})
                    floors = (await ws.receive_json()).get("result", [])
                    return JSONResponse({
                        "status": "success",
                        "message": f"Kết nối thành công! Tìm thấy {len(floors)} tầng, {len(areas)} phòng.",
                        "floors_count": len(floors),
                        "areas_count": len(areas)
                    })
                else:
                    return JSONResponse({
                        "status": "error",
                        "message": f"Xác thực thất bại: {auth_res.get('message', 'Token không đúng')}"
                    }, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": f"Lỗi kết nối: {str(e)}"}, status_code=400)

# -----------------------------------------------------------------------------
# FIRMWARE OTA UPDATE APIS & WEBSOCKET BROADCAST
# -----------------------------------------------------------------------------
class OTAStartRequest(BaseModel):
    target: str = "all" # "all" hoặc pairing_code cụ thể (vd: "881C")
    firmware_filename: Optional[str] = "firmware_latest.bin"

@app.post("/api/ota/upload")
async def upload_firmware(request: Request, filename: Optional[str] = None, version: Optional[str] = None):
    """Tải lên file firmware .bin biên dịch từ PlatformIO để cập nhật OTA."""
    content_type = request.headers.get("content-type", "")
    fname = filename or "firmware.bin"
    ver = version or ""
    content = b""

    if "multipart/form-data" in content_type:
        try:
            form = await request.form()
            file = form.get("file")
            if file and hasattr(file, "filename"):
                fname = file.filename
                ver = form.get("version") or ver
                content = await file.read()
        except Exception:
            content = await request.body()
    else:
        # Binary stream upload (không phụ thuộc python-multipart)
        fname = filename or request.headers.get("x-filename") or "firmware.bin"
        ver = version or request.headers.get("x-version") or ""
        content = await request.body()

    if not fname.endswith(".bin"):
        return JSONResponse({"status": "error", "message": "Chỉ chấp nhận file firmware có đuôi .bin"}, status_code=400)

    file_size = len(content)
    if file_size < 100000:
        return JSONResponse({"status": "error", "message": "File firmware quá nhỏ (<100KB), không hợp lệ"}, status_code=400)

    md5_hash = hashlib.md5(content).hexdigest()

    # Lưu bản mới nhất
    latest_path = os.path.join(FIRMWARE_DIR, "firmware_latest.bin")
    with open(latest_path, "wb") as f:
        f.write(content)

    # Lưu bản backup có timestamp
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_str = ver.strip() if ver else f"v_{ts_str}"
    backup_filename = f"firmware_{ts_str}_{fname}"
    backup_path = os.path.join(FIRMWARE_DIR, backup_filename)
    with open(backup_path, "wb") as f:
        f.write(content)

    host = request.headers.get("host", f"192.168.1.114:{PORT}") if request else f"192.168.1.114:{PORT}"
    if "localhost" in host or "127.0.0.1" in host:
        host = f"192.168.1.114:{PORT}"

    download_url = f"http://{host}/api/ota/firmware/firmware_latest.bin"

    meta = {
        "latest_file": "firmware_latest.bin",
        "original_filename": fname,
        "version": version_str,
        "size_bytes": file_size,
        "size_mb": round(file_size / (1024 * 1024), 2),
        "md5": md5_hash,
        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "download_url": download_url
    }

    meta_path = os.path.join(FIRMWARE_DIR, "ota_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    logger.info("Firmware uploaded: %s (%s MB, MD5: %s, Ver: %s)", fname, meta["size_mb"], md5_hash, version_str)

    await broadcast_to_admins({
        "type": "ota_firmware_uploaded",
        "meta": meta
    })

    return JSONResponse({
        "status": "success",
        "message": f"Đã tải lên thành công firmware [{fname}] ({meta['size_mb']} MB)!",
        "meta": meta
    })

@app.get("/api/ota/status")
async def get_ota_status(request: Request):
    """Lấy thông tin bản firmware OTA hiện có trên NAS Hub."""
    meta_path = os.path.join(FIRMWARE_DIR, "ota_meta.json")
    if not os.path.exists(meta_path):
        return JSONResponse({"available": False})
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        host = request.headers.get("host", f"192.168.1.114:{PORT}")
        if "localhost" in host or "127.0.0.1" in host:
            host = f"192.168.1.114:{PORT}"
        meta["available"] = True
        meta["download_url"] = f"http://{host}/api/ota/firmware/firmware_latest.bin"
        return JSONResponse(meta)
    except Exception as e:
        return JSONResponse({"available": False, "error": str(e)})

@app.get("/api/ota/firmware/{filename}")
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
    })

    return JSONResponse({
        "status": "success",
        "message": f"Đã phát lệnh cập nhật OTA cho {sent_count} màn hình!",
        "sent_count": sent_count,
        "url": firmware_url
    })

# -----------------------------------------------------------------------------
# VOICE & INTERCOM HISTORY APIS & AUTO-CLEANUP
# -----------------------------------------------------------------------------
class HistorySettingsRequest(BaseModel):
    retention_days: int

@app.get("/api/history")
async def get_history(limit: int = 100, type: Optional[str] = None):
    """Lấy danh sách lịch sử STT giọng nói và đàm thoại nội bộ."""
    records = history_mgr.get_records(limit=limit, filter_type=type)
    return JSONResponse({
        "status": "success",
        "records": records,
        "settings": history_mgr.get_settings()
    })

@app.get("/api/history/audio/{filename}")
async def get_history_audio(filename: str):
    """Nghe lại file âm thanh WAV đã ghi âm."""
    path = history_mgr.get_audio_path(filename)
    if path and os.path.exists(path):
        return FileResponse(path, media_type="audio/wav")
    return JSONResponse({"status": "error", "message": "File âm thanh không tồn tại"}, status_code=404)

@app.get("/api/history/settings")
async def get_history_settings():
    return JSONResponse(history_mgr.get_settings())

@app.post("/api/history/settings")
async def update_history_settings(req: HistorySettingsRequest):
    updated = history_mgr.update_settings(req.retention_days)
    return JSONResponse({"status": "success", "settings": updated})

@app.delete("/api/history")
async def clear_all_history():
    count = history_mgr.clear_all()
    await broadcast_to_admins({"type": "history_cleared"})
    return JSONResponse({"status": "success", "message": f"Đã dọn sạch {count} bản ghi lịch sử."})

@app.delete("/api/history/{record_id}")
async def delete_history_item(record_id: str):
    success = history_mgr.delete_record(record_id)
    if success:
        await broadcast_to_admins({"type": "history_deleted", "id": record_id})
        return JSONResponse({"status": "success", "message": "Đã xóa bản ghi"})
    return JSONResponse({"status": "error", "message": "Bản ghi không tồn tại"}, status_code=404)

# -----------------------------------------------------------------------------
# WEBSOCKET ENDPOINTS FOR ESP32 PANELS, NODES & WEB ADMIN
# -----------------------------------------------------------------------------
@app.websocket("/")
@app.websocket("/ws")
@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str = "default_panel"):
    await websocket.accept()
    active_sockets[device_id] = websocket
    audio_record_buffers[device_id] = bytearray()
    logger.info("New WebSocket connection: %s", device_id)

    dev_code: Optional[str] = None

    # Nếu kết nối là Web Admin Dashboard -> Gửi ngay toàn bộ dữ liệu khởi tạo
    if device_id.startswith("web_admin"):
        intercom.register_admin(websocket)
        try:
            await websocket.send_json({
                "type": "init",
                "devices": get_devices_list(),
                "system": {
                    "nas_hub": {"status": "online", "port": PORT},
                    "ha_connected": ha_bridge.authenticated,
                    "ha_url": ha_bridge.ws_url,
                    "active_sockets": len(active_sockets)
                },
                "entities": ha_bridge.get_entities_list(),
                "areas": ha_bridge.get_areas_list(),
                "floors": ha_bridge.get_floors_list(),
                "intercom_targets": intercom.get_targets(),
                "history_settings": history_mgr.get_settings()
            })
        except Exception as e:
            logger.error("Failed to send init to web_admin: %s", e)

    try:
        while True:
            message = await websocket.receive()

            # 1. TEXT FRAME (JSON Control, Register, HA Action, Config)
            if "text" in message:
                data = json.loads(message["text"])
                msg_type = data.get("type")

                # Đăng ký thiết bị khi Panel vừa kết nối
                if msg_type == "register":
                    payload = data.get("payload", {})
                    mac = payload.get("mac", "")
                    code = payload.get("pairing_code", "").upper()
                    ip = payload.get("ip", "")
                    model = payload.get("model", "ES3C28P")

                    if code:
                        dev_code = code
                        active_sockets[code] = websocket
                        if code not in devices_db:
                            assigned_intercom_id = intercom.assign_id(code)
                            devices_db[code] = {
                                "device_id": f"panel_{code.lower()}",
                                "mac": mac,
                                "pairing_code": code,
                                "ip": ip,
                                "model": model,
                                "room_name": "Phòng Khách",
                                "floor": "Tầng Trệt",
                                "is_paired": False,
                                "online": True,
                                "intercom_id": assigned_intercom_id,
                                "buttons": [
                                    {"id": "btn_1", "name": "Đèn Phòng", "entity_id": "light.moes_matter_switch_den_3_6", "icon": "light"},
                                    {"id": "btn_2", "name": "Máy Lạnh", "entity_id": "climate.151732606266034_climate", "icon": "climate"}
                                ],
                                "entities": ["light.moes_matter_switch_den_3_6", "climate.151732606266034_climate"],
                                "settings": {"brightness": 90, "volume": 80, "ai_model": "gemini"}
                            }
                            save_devices()
                            logger.info("New Panel Discovered! Code: [%s], MAC: %s, IP: %s", code, mac, ip)
                        else:
                            # Cập nhật IP mới và trạng thái online
                            devices_db[code]["ip"] = ip
                            devices_db[code]["online"] = True
                            if "intercom_id" not in devices_db[code]:
                                devices_db[code]["intercom_id"] = intercom.assign_id(code)
                            save_devices()

                        dev = devices_db[code]
                        assigned_intercom_id = dev.get("intercom_id", 1)
                        intercom.register(code, websocket, assigned_intercom_id, meta={
                            "room_name": dev.get("room_name", f"Panel {code}"),
                            "floor": dev.get("floor", "")
                        })

                        # Tự động sync cấu hình đã lưu xuống Panel kèm kênh đàm thoại
                        targets = intercom.get_targets(exclude_device_key=code)
                        await websocket.send_json({
                            "type": "config_sync",
                            "payload": {
                                "room": f"{dev['room_name']} - {dev['floor']}",
                                "floor": dev['floor'],
                                "my_intercom_id": assigned_intercom_id,
                                "intercom_targets": targets,
                                "buttons": get_buttons_with_state(dev),
                                "entities": dev.get("entities", []),
                                "settings": dev.get("settings", {})
                            }
                        })
                        logger.info("Auto-synced existing configuration to Panel [%s] (Intercom ID: %d, Targets: %d)", code, assigned_intercom_id, len(targets))

                        # Đồng bộ danh sách kênh Intercom mới tới các màn hình khác đang online
                        for code_k, ws_k in list(active_sockets.items()):
                            if not code_k.startswith("web_admin") and code_k != code and code_k != "default_panel":
                                try:
                                    await ws_k.send_json({
                                        "type": "intercom_sync",
                                        "payload": {
                                            "my_intercom_id": devices_db.get(code_k, {}).get("intercom_id", 1),
                                            "targets": intercom.get_targets(exclude_device_key=code_k)
                                        }
                                    })
                                except Exception:
                                    pass

                        # Thông báo ngay lập tức tới tất cả Web Admin Dashboard
                        await broadcast_to_admins({
                            "type": "devices_update",
                            "devices": get_devices_list(),
                            "intercom_targets": intercom.get_targets()
                        })

                # Điều khiển thiết bị Home Assistant từ Panel hoặc Web Admin
                elif msg_type == "ha_action":
                    payload = data.get("payload", {})
                    entity_id = payload.get("entity_id", "")
                    domain = payload.get("domain") or (entity_id.split(".")[0] if "." in entity_id else "light")
                    service = payload.get("service", "toggle")
                    if entity_id:
                        if domain == "climate" and service == "toggle":
                            cur_st = ha_bridge.states.get(entity_id, {}).get("state", "off")
                            target_mode = "off" if cur_st not in ["off", "unavailable"] else "cool"
                            await ha_bridge.call_service(
                                domain="climate",
                                service="set_hvac_mode",
                                entity_id=entity_id,
                                service_data={"hvac_mode": target_mode}
                            )
                        else:
                            await ha_bridge.call_service(
                                domain=domain,
                                service=service,
                                entity_id=entity_id
                            )

                # Ping chẩn đoán từ màn hình ESP32 hoặc Web Admin
                elif msg_type == "ping":
                    client_time = data.get("client_time", 0)
                    await websocket.send_json({
                        "type": "pong",
                        "client_time": client_time,
                        "server_time": int(time.time() * 1000)
                    })

                # Lệnh trực tiếp từ Web Admin gửi qua WebSocket
                elif msg_type == "admin_action":
                    action = data.get("action")
                    if action == "toggle_entity":
                        entity_id = data.get("entity_id", "")
                        domain = entity_id.split(".")[0] if "." in entity_id else "light"
                        if domain == "climate":
                            cur_st = ha_bridge.states.get(entity_id, {}).get("state", "off")
                            target_mode = "off" if cur_st not in ["off", "unavailable"] else "cool"
                            await ha_bridge.call_service(domain="climate", service="set_hvac_mode", entity_id=entity_id, service_data={"hvac_mode": target_mode})
                        else:
                            await ha_bridge.call_service(domain=domain, service="toggle", entity_id=entity_id)
                    elif action == "sync_panel":
                        target_code = data.get("pairing_code", "").upper()
                        dev = devices_db.get(target_code)
                        if dev:
                            target_ws = active_sockets.get(target_code) or active_sockets.get(dev.get("device_id"))
                            if target_ws:
                                await target_ws.send_json({
                                    "type": "config_sync",
                                    "payload": {
                                        "room": f"{dev.get('room_name', 'Phong Khach')} - {dev.get('floor', 'Tang Tret')}",
                                        "floor": dev.get('floor', 'Tang Tret'),
                                        "buttons": get_buttons_with_state(dev),
                                        "entities": dev.get("entities", []),
                                        "settings": dev.get("settings", {})
                                    }
                                })
                                logger.info("WS Admin triggered config_sync for [%s]", target_code)

                # Điều khiển phiên (AI voice / Intercom call)
                elif msg_type == "session_control":
                    payload = data.get("payload", {})
                    action = payload.get("action")
                    if action == "stop_ptt" and len(audio_record_buffers[device_id]) > 0:
                        pcm_audio = bytes(audio_record_buffers[device_id])
                        audio_record_buffers[device_id].clear()
                        asyncio.create_task(handle_ai_voice_flow(device_id, websocket, pcm_audio))

                # Phản hồi tiến độ cập nhật OTA từ màn hình Panel
                elif msg_type == "ota_progress":
                    progress = data.get("progress", 0)
                    status = data.get("status", "progress") # "downloading", "flashing", "success", "error"
                    msg = data.get("message", "")
                    code = data.get("pairing_code", dev_code or "")
                    logger.info("OTA Progress from [%s]: %s%% (%s) - %s", code, progress, status, msg)
                    await broadcast_to_admins({
                        "type": "ota_progress",
                        "pairing_code": code,
                        "progress": progress,
                        "status": status,
                        "message": msg
                    })

            # 2. BINARY FRAME (Raw PCM 16kHz 520 Bytes)
            elif "bytes" in message:
                packet = message["bytes"]
                if len(packet) == 520:
                    sender_key = dev_code or device_id
                    target_id = packet[3]
                    # Nếu là gói tin gửi cho AI (target_id == 0x00)
                    if target_id == 0x00:
                        stream_flag = packet[6]
                        pcm_chunk = packet[7:519]
                        if stream_flag == 0x01: # START
                            audio_record_buffers[sender_key].clear()
                        audio_record_buffers[sender_key].extend(pcm_chunk)
                        if stream_flag == 0x03: # END
                            pcm_audio = bytes(audio_record_buffers[sender_key])
                            audio_record_buffers[sender_key].clear()
                            asyncio.create_task(handle_ai_voice_flow(sender_key, websocket, pcm_audio))
                    else:
                        # Gói tin đàm thoại nội bộ Intercom -> Lưu buffer âm thanh và định tuyến
                        stream_flag = packet[6]
                        pcm_chunk = packet[7:519]
                        if stream_flag == 0x01: # START
                            intercom_audio_buffers[sender_key] = bytearray()
                        if sender_key in intercom_audio_buffers:
                            intercom_audio_buffers[sender_key].extend(pcm_chunk)
                        if stream_flag == 0x03 and sender_key in intercom_audio_buffers: # END
                            ic_pcm = bytes(intercom_audio_buffers[sender_key])
                            del intercom_audio_buffers[sender_key]
                            dev = devices_db.get(sender_key, {})
                            r_name = dev.get("room_name", f"Thiết bị {sender_key}")
                            rec = history_mgr.add_record(
                                device_code=sender_key,
                                room_name=r_name,
                                session_type="intercom",
                                text="Đàm thoại nội bộ",
                                response="",
                                pcm_data=ic_pcm
                            )
                            asyncio.create_task(broadcast_to_admins({"type": "history_new", "record": rec}))

                        await intercom.route_binary_packet(sender_key, packet)

    except WebSocketDisconnect:
        logger.info("Device disconnected: %s", dev_code or device_id)
    except Exception as e:
        logger.error("Error in websocket session for %s: %s", dev_code or device_id, e)
    finally:
        current_key = dev_code or device_id
        intercom.unregister(current_key)
        if device_id.startswith("web_admin"):
            intercom.unregister_admin(websocket)
        if current_key in active_sockets:
            del active_sockets[current_key]
        if device_id in active_sockets and device_id != current_key:
            del active_sockets[device_id]
        if dev_code and dev_code in active_sockets and dev_code != current_key:
            del active_sockets[dev_code]
        if current_key in audio_record_buffers:
            del audio_record_buffers[current_key]

        # Cập nhật danh sách thiết bị cho Admin khi có thiết bị ngắt kết nối
        if not device_id.startswith("web_admin"):
            await broadcast_to_admins({
                "type": "devices_update",
                "devices": get_devices_list(),
                "intercom_targets": intercom.get_targets()
            })

async def handle_ai_voice_flow(device_id: str, ws: WebSocket, pcm_audio: bytes):
    """Luồng xử lý giọng nói hoàn chỉnh: STT -> AI Intent / HA Action -> TTS -> Gửi Binary Audio về ESP32."""
    try:
        await ws.send_json({"type": "ai_state", "payload": {"state": "thinking"}})

        # 1. Faster-Whisper STT
        text = await audio_pipeline.pcm_to_text(pcm_audio)
        if not text:
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": "Không nhận diện được giọng nói."}})
            return

        # 2. AI Intent & Home Assistant Action
        response_text = await ai_router.process_intent(text)
        await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": response_text}})

        # Lưu vào Lịch sử Giọng nói & Ghi âm Audio
        dev = devices_db.get(device_id, {})
        room_name = dev.get("room_name", f"Panel {device_id}")
        rec = history_mgr.add_record(
            device_code=device_id,
            room_name=room_name,
            session_type="voice_ai",
            text=text,
            response=response_text,
            pcm_data=pcm_audio
        )
        asyncio.create_task(broadcast_to_admins({"type": "history_new", "record": rec}))

        # 3. Piper TTS
        response_pcm = await audio_pipeline.text_to_pcm(response_text)
        if response_pcm:
            seq = 0
            for i in range(0, len(response_pcm), 512):
                chunk = response_pcm[i:i+512]
                if len(chunk) < 512:
                    chunk = chunk + b'\x00' * (512 - len(chunk))

                flag = 0x01 if i == 0 else (0x03 if i + 512 >= len(response_pcm) else 0x02)
                header = bytearray(7)
                header[0:2] = (0xA55A).to_bytes(2, 'little')
                header[2] = 0x00 # Server sender
                header[3] = 0x01 # Target ESP32
                header[4:6] = seq.to_bytes(2, 'little')
                header[6] = flag

                packet = header + chunk + b'\x00'
                await ws.send_bytes(bytes(packet))
                seq += 1
                await asyncio.sleep(0.015)

        await ws.send_json({"type": "ai_state", "payload": {"state": "idle"}})

    except Exception as e:
        logger.error("Error in AI voice flow for %s: %s", device_id, e)
        await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": "Lỗi xử lý âm thanh."}})

if __name__ == "__main__":
    uvicorn.run("app.main_ws_server:app", host="0.0.0.0", port=PORT, reload=False)
