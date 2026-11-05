"""
NALA SMART HOME - CENTRAL WEBSOCKET SERVER & WEB MANAGEMENT HUB
Handles WebSocket connections from ESP32-S3 Wall Panels and ESP32-C3 Nodes.
Coordinates Device Pairing, Web Management Hub, HA Bridge, Audio Pipeline, and Intercom.
"""

import os
import json
import asyncio
import time
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
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

def get_buttons_with_state(dev: dict, include_all_house_active: bool = False) -> list:
    """Đính kèm trạng thái thực tế từ HA vào các nút bấm của panel, kèm các thiết bị đang bật toàn nhà."""
    buttons_with_state = []
    local_room_name = dev.get("room_name", "")
    local_eids = set()

    # 1. Các nút cấu hình riêng cho phòng của màn hình này
    for b in dev.get("buttons", []):
        b_copy = dict(b)
        eid = b.get("entity_id", "")
        if eid:
            local_eids.add(eid)
            raw_s = ha_bridge.states.get(eid, {})
            cur_state = raw_s.get("state", "off")
            b_copy["state"] = cur_state
            b_copy["is_on"] = (cur_state == "on" or (cur_state not in ["off", "unavailable", "unknown", ""]))
            raw_attrs = raw_s.get("attributes", {})
            b_copy["attributes"] = {
                k: raw_attrs[k] for k in ["temperature", "current_temperature", "hvac_mode", "fan_mode", "swing_mode"] if k in raw_attrs
            }
            if not b_copy.get("domain"):
                b_copy["domain"] = eid.split(".")[0] if "." in eid else "light"
        else:
            b_copy["state"] = "off"
            b_copy["is_on"] = False
        if not b_copy.get("room"):
            b_copy["room"] = local_room_name
        b_copy["local"] = True
        buttons_with_state.append(b_copy)

    # 2. Tự động gom thêm các thiết bị đang BẬT trên toàn nhà (nếu include_all_house_active=True)
    if include_all_house_active:
        cfg = load_all_house_config()
        excluded_entities = set(cfg.get("excluded_entities", []))
        all_ents = ha_bridge.get_entities_list()

        def shorten_room(name: str) -> str:
            name = name.replace("Phòng ", "P.").replace("phòng ", "P.")
            if len(name) > 8:
                return name[:8]
            return name

        def shorten_device(name: str) -> str:
            name = name.replace("Máy lạnh", "M.Lạnh").replace("máy lạnh", "M.Lạnh")
            name = name.replace("Đèn trần", "Đèn").replace("đèn trần", "Đèn")
            name = name.replace("Công tắc", "CT").replace("công tắc", "CT")
            if len(name) > 10:
                return name[:10]
            return name

        for e in all_ents:
            eid = e.get("entity_id", "")
            if not eid or eid in local_eids or eid in excluded_entities:
                continue
            domain = e.get("domain", "")
            st = e.get("state", "off")
            is_on = (st in ["on", "true", "open"]) or (domain == "climate" and st not in ["off", "unavailable", "unknown", ""])
            if not is_on:
                continue

            area_name = e.get("area_name") or "Khác"
            device_name = e.get("name") or (eid.split(".")[1] if "." in eid else eid)
            short_r = shorten_room(area_name)
            short_d = shorten_device(device_name)
            display_label = f"{short_r}: {short_d}"

            raw_s = ha_bridge.states.get(eid, {})
            buttons_with_state.append({
                "id": f"ha_{eid.replace('.', '_')}",
                "name": display_label,
                "entity_id": eid,
                "icon": domain,
                "room": area_name,
                "state": st,
                "is_on": True,
                "attributes": raw_s.get("attributes", {}),
                "local": False
            })

            # Tối đa 30 nút cho ESP32 LVGL
            if len(buttons_with_state) >= 30:
                break

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
                    dev["online"] = False # Khi server vừa khởi động, chưa có socket nào kết nối
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
        ws = active_sockets.get(code)
        # Thiết bị chỉ ONLINE khi có kết nối WebSocket thực tế đang hoạt động trong active_sockets & intercom
        is_conn = (ws is not None and code in intercom.connections)
        dev["online"] = is_conn
        if "intercom_id" not in dev:
            dev["intercom_id"] = intercom.get_id(code) or intercom.assign_id(code)
    return list(devices_db.values())

def get_all_rooms_summary(local_room: str = "") -> list:
    """
    Tổng hợp danh sách các phòng và số lượng thiết bị đang bật từ Home Assistant và các màn hình NALA.
    Ưu tiên:
    1. Phòng hiện tại của màn hình (local_room)
    2. Các phòng đang có thiết bị BẬT (active_devices_count > 0)
    3. Các phòng còn lại trong ngôi nhà.
    """
    rooms = []
    seen_area_ids = set()

    # 1. Thu thập danh sách từ Home Assistant
    areas = ha_bridge.get_areas_list()
    all_ents = ha_bridge.get_entities_list()

    cfg = load_all_house_config()
    excluded_entities = set(cfg.get("excluded_entities", []))

    entities_by_area = {}
    for e in all_ents:
        eid = e.get("entity_id", "")
        if eid in excluded_entities:
            continue
        aid = e.get("area_id") or "other"
        st = e.get("state", "off")
        domain = e.get("domain", "")
        if domain not in ["light", "climate", "fan", "switch"]:
            continue
        is_on = (st in ["on", "true", "open"]) or (domain == "climate" and st not in ["off", "unavailable", "unknown", ""])
        # Gioi han toi da 8 thiet bi moi phong vi ESP32 chi hien thi toi da 8 thiet bi
        room_list = entities_by_area.setdefault(aid, [])
        if len(room_list) < 8:
            room_list.append({
            "entity_id": eid,
            "name": e.get("name") or eid,
            "domain": domain,
            "state": st,
            "is_on": is_on
        })

    for a in areas:
        aid = a.get("area_id")
        if not aid:
            continue
        seen_area_ids.add(aid)
        aname = a.get("name", aid)
        a_ents = entities_by_area.get(aid, [])
        active_count = sum(1 for item in a_ents if item["is_on"])

        room_buttons = []
        for item in a_ents:
            eid = item["entity_id"]
            dname = item["name"]
            dname = dname.replace("Máy lạnh", "M.Lạnh").replace("máy lạnh", "M.Lạnh")
            dname = dname.replace("Đèn trần", "Đèn").replace("đèn trần", "Đèn")
            dname = dname.replace("Công tắc", "CT").replace("công tắc", "CT")
            raw_s = ha_bridge.states.get(eid, {})
            raw_attrs = raw_s.get("attributes", {})
            slim_attrs = {}
            if "temperature" in raw_attrs:
                slim_attrs["temperature"] = raw_attrs["temperature"]
            if "current_temperature" in raw_attrs:
                slim_attrs["current_temperature"] = raw_attrs["current_temperature"]
            room_buttons.append({
                "id": f"ha_{eid.replace('.', '_')}",
                "name": dname[:14],
                "entity_id": eid,
                "icon": item["domain"],
                "room": aname,
                "is_on": item["is_on"],
                "state": item["state"],
                "attributes": slim_attrs
            })

        rooms.append({
            "room_id": aid,
            "room_name": aname,
            "floor": a.get("floor_name", a.get("floor_id", "")),
            "active_devices_count": active_count,
            "total_devices_count": len(a_ents),
            "buttons": room_buttons
        })

    # Nếu có panel trong devices_db có phòng chưa có trong areas của HA, bổ sung vào
    for code, dev in devices_db.items():
        if not dev.get("is_paired", False):
            continue
        rname = dev.get("room_name", "")
        if rname and not any(r["room_name"].lower() == rname.lower() for r in rooms):
            btns = get_buttons_with_state(dev, include_all_house_active=False)
            active_count = sum(1 for b in btns if b.get("is_on", False))
            rooms.append({
                "room_id": f"panel_{code}",
                "room_name": rname,
                "floor": dev.get("floor", ""),
                "active_devices_count": active_count,
                "total_devices_count": len(btns),
                "buttons": btns
            })

    # Sắp xếp danh sách phòng:
    # 1) Phòng trùng với local_room đưa lên đầu
    # 2) Các phòng có active_devices_count > 0 (sắp xếp giảm dần theo active count)
    # 3) Các phòng còn lại
    def room_sort_key(r):
        is_local = 0 if (local_room and r["room_name"].lower() in local_room.lower()) else 1
        has_active = 0 if r["active_devices_count"] > 0 else 1
        return (is_local, has_active, -r["active_devices_count"], r["room_name"])

    rooms.sort(key=room_sort_key)
    return rooms[:12]

# All-House Master Configuration File
ALL_HOUSE_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "all_house_config.json")
DEFAULT_ALL_HOUSE_CONFIG = {
    "enabled": True,
    "action_mode": "turn_off_selected",
    "controlled_domains": ["light", "fan"],
    "include_climate": False,
    "include_switch": False,
    "excluded_entities": [],
    "scene_entity_id": "",
    "confirm_prompt": False,
    "alert_title": "TOÀN BỘ NHÀ",
    "room_view_timeout": 15
}

def load_all_house_config() -> dict:
    if os.path.exists(ALL_HOUSE_CONFIG_FILE):
        try:
            with open(ALL_HOUSE_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                res = DEFAULT_ALL_HOUSE_CONFIG.copy()
                res.update(cfg)
                return res
        except Exception as e:
            logger.error("Error loading all_house_config.json: %s", e)
    return DEFAULT_ALL_HOUSE_CONFIG.copy()

def save_all_house_config(cfg: dict) -> bool:
    try:
        with open(ALL_HOUSE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("Error saving all_house_config.json: %s", e)
        return False

def get_house_status_summary() -> dict:
    """Tính toán tổng số đèn, quạt, thiết bị đang bật trên toàn nhà dựa theo cấu hình Master Toàn Nhà."""
    cfg = load_all_house_config()
    controlled_domains = set(cfg.get("controlled_domains", ["light", "fan"]))
    include_climate = cfg.get("include_climate", False)
    include_switch = cfg.get("include_switch", False)
    excluded_entities = set(cfg.get("excluded_entities", []))

    total_on_lights = 0
    total_on_fans = 0
    total_on_climates = 0
    total_on_switches = 0
    total_on_devices = 0
    
    for eid, raw in ha_bridge.states.items():
        if eid in excluded_entities:
            continue
        st = raw.get("state", "off")
        domain = eid.split(".")[0] if "." in eid else ""

        if domain == "light" and "light" in controlled_domains:
            if st in ["on", "true", "open"]:
                total_on_lights += 1
                total_on_devices += 1
        elif domain == "fan" and "fan" in controlled_domains:
            if st in ["on", "true", "open"]:
                total_on_fans += 1
                total_on_devices += 1
        elif domain == "climate" and include_climate:
            if st not in ["off", "unavailable", "unknown", ""]:
                total_on_climates += 1
                total_on_devices += 1
        elif domain == "switch" and include_switch:
            if st in ["on", "true", "open"]:
                total_on_switches += 1
                total_on_devices += 1

    summary_parts = []
    if total_on_lights > 0:
        summary_parts.append(f"{total_on_lights} ĐÈN")
    if total_on_fans > 0:
        summary_parts.append(f"{total_on_fans} QUẠT")
    if total_on_climates > 0:
        summary_parts.append(f"{total_on_climates} MLẠNH")
    if total_on_switches > 0:
        summary_parts.append(f"{total_on_switches} CÔNG TẮC")

    if summary_parts:
        summary_text = " & ".join(summary_parts) + " ĐANG BẬT"
    else:
        summary_text = "ĐÃ TẮT HẾT CÁC PHÒNG"

    return {
        "total_on_lights": total_on_lights,
        "total_on_fans": total_on_fans,
        "total_on_climates": total_on_climates,
        "total_on_switches": total_on_switches,
        "total_on_devices": total_on_devices,
        "summary_text": summary_text,
        "excluded_count": len(excluded_entities)
    }

def get_floors_overview() -> dict:
    """Tổng hợp cây phân tầng (Floor & Room Tree) và trạng thái thiết bị thời gian thực."""
    cfg = load_all_house_config()
    excluded_entities = set(cfg.get("excluded_entities", []))

    floors = ha_bridge.get_floors_list()
    areas = ha_bridge.get_areas_list()
    all_ents = ha_bridge.get_entities_list()

    DEFAULT_FLOOR_ORDER = [
        {"floor_id": "tret", "floor_name": "Tầng Trệt", "level": 0},
        {"floor_id": "tang1", "floor_name": "Tầng 1", "level": 1},
        {"floor_id": "tang2", "floor_name": "Tầng 2", "level": 2},
        {"floor_id": "tang_3", "floor_name": "Tầng 3", "level": 3},
        {"floor_id": "other", "floor_name": "Khu Vực Khác", "level": 99}
    ]

    floor_name_map = {}
    for f in DEFAULT_FLOOR_ORDER:
        floor_name_map[f["floor_id"]] = f["floor_name"]
    for f in floors:
        fid = f.get("floor_id")
        if fid:
            fname = f.get("name", fid)
            if fid == "tret": fname = "Tầng Trệt"
            elif fid == "tang1": fname = "Tầng 1"
            elif fid == "tang2": fname = "Tầng 2"
            elif fid == "tang_3": fname = "Tầng 3"
            floor_name_map[fid] = fname

    entities_by_area = {}
    for e in all_ents:
        aid = e.get("area_id") or "other"
        eid = e.get("entity_id", "")
        if eid in excluded_entities:
            continue
        domain = e.get("domain", "")
        st = e.get("state", "off")
        is_on = (st in ["on", "true", "open"]) or (domain == "climate" and st not in ["off", "unavailable", "unknown", ""])
        entities_by_area.setdefault(aid, []).append({
            "entity_id": eid,
            "name": e.get("name") or eid,
            "domain": domain,
            "state": st,
            "is_on": is_on
        })

    areas_by_floor = {}
    for a in areas:
        aid = a.get("area_id")
        fid = a.get("floor_id") or "other"
        aname = a.get("name", aid)
        a_ents = entities_by_area.get(aid, [])
        active_count = sum(1 for item in a_ents if item["is_on"])
        areas_by_floor.setdefault(fid, []).append({
            "area_id": aid,
            "name": aname,
            "icon": a.get("icon") or "mdi:home-outline",
            "active_count": active_count,
            "total_count": len(a_ents),
            "entities": a_ents
        })

    result_floors = []
    total_house_active = 0
    for f_def in DEFAULT_FLOOR_ORDER:
        fid = f_def["floor_id"]
        fname = floor_name_map.get(fid, f_def["floor_name"])
        f_areas = areas_by_floor.get(fid, [])
        f_areas.sort(key=lambda x: (0 if x["active_count"] > 0 else 1, x["name"]))
        floor_active = sum(ar["active_count"] for ar in f_areas)
        floor_total = sum(ar["total_count"] for ar in f_areas)
        total_house_active += floor_active
        result_floors.append({
            "floor_id": fid,
            "floor_name": fname,
            "level": f_def["level"],
            "active_count": floor_active,
            "total_count": floor_total,
            "areas": f_areas
        })

    return {
        "total_active_devices": total_house_active,
        "floors": result_floors
    }

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
    is_on = (new_state == "on" or (new_state not in ["off", "unavailable", "unknown", ""]))
    attrs = raw_obj.get("attributes", {}) if isinstance(raw_obj, dict) else {}
    house_status = get_house_status_summary()
    floors_overview = get_floors_overview()
    all_rooms_default = get_all_rooms_summary()

    base_msg = {
        "type": "ha_state_change",
        "payload": {
            "entity_id": entity_id,
            "state": new_state,
            "is_on": is_on,
            "attributes": attrs,
            "house_status": house_status,
            "floors_overview": floors_overview,
            "all_rooms": all_rooms_default
        }
    }

    for dev_id, ws in list(active_sockets.items()):
        try:
            if dev_id.startswith("web_admin"):
                await ws.send_json(base_msg)
            else:
                # Gửi cho màn hình ESP32: kèm buttons và all_rooms ưu tiên phòng hiện tại
                dev = devices_db.get(dev_id)
                if dev:
                    panel_msg = {
                        "type": "ha_state_change",
                        "payload": {
                            "entity_id": entity_id,
                            "state": new_state,
                            "is_on": is_on,
                            "attributes": attrs,
                            "house_status": house_status,
                            "all_rooms": get_all_rooms_summary(local_room=dev.get("room_name", "")),
                            "buttons": get_buttons_with_state(dev, include_all_house_active=False)
                        }
                    }
                    await ws.send_json(panel_msg)
                else:
                    await ws.send_json(base_msg)
        except Exception:
            pass

async def device_heartbeat_task():
    """Kiểm tra định kỳ liveness của kết nối WebSocket tới các màn hình ESP32 (mỗi 10s).
    Nếu màn hình bị rút điện hoặc mất WiFi, việc gửi ping sẽ phát hiện lỗi và đánh dấu OFFLINE ngay."""
    while True:
        try:
            await asyncio.sleep(10)
            dead_panels = []
            for code, ws in list(active_sockets.items()):
                if code.startswith("web_admin") or code == "default_panel":
                    continue
                try:
                    # Gửi frame ping nhỏ kiểm tra kết nối với timeout 3s
                    await asyncio.wait_for(
                        ws.send_json({"type": "server_ping", "ts": int(time.time() * 1000)}),
                        timeout=3.0
                    )
                except Exception as ex:
                    logger.warning("Heartbeat ping failed for panel [%s]: %s -> Marking OFFLINE", code, ex)
                    dead_panels.append((code, ws))

            if dead_panels:
                for code, ws in dead_panels:
                    if active_sockets.get(code) == ws:
                        del active_sockets[code]
                    intercom.unregister(code, ws)
                    if code in devices_db:
                        devices_db[code]["online"] = False
                    try:
                        await ws.close()
                    except Exception:
                        pass
                
                logger.info("Broadcast devices_update after heartbeat detected dead panels: %s", [c for c, _ in dead_panels])
                await broadcast_to_admins({
                    "type": "devices_update",
                    "devices": get_devices_list(),
                    "intercom_targets": intercom.get_targets()
                })
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in device heartbeat task: %s", e)

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
    asyncio.create_task(device_heartbeat_task())

# -----------------------------------------------------------------------------
# WEB MANAGEMENT HUB & REST APIS
# -----------------------------------------------------------------------------
@app.get("/")
@app.get("/admin")
async def get_admin_dashboard():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            html = f.read()
        return HTMLResponse(
            html,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
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
            "online": (code in active_sockets and code in intercom.connections)
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
            "buttons": get_buttons_with_state(dev, include_all_house_active=False),
            "all_rooms": get_all_rooms_summary(local_room=req.room_name),
            "house_status": get_house_status_summary(),
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
        rname = dev.get("room_name", "Phong Khach")
        assigned_id = dev.get("intercom_id") or intercom.get_id(code) or 1
        sync_msg = {
            "type": "config_sync",
            "payload": {
                "room": f"{rname} - {dev.get('floor', 'Tang Tret')}",
                "floor": dev.get('floor', 'Tang Tret'),
                "my_intercom_id": assigned_id,
                "intercom_targets": intercom.get_targets(exclude_device_key=code),
                "buttons": get_buttons_with_state(dev, include_all_house_active=False),
                "all_rooms": get_all_rooms_summary(local_room=rname),
                "house_status": get_house_status_summary(),
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
    service_data: Optional[dict] = None

@app.post("/api/ha/call_service")
async def call_ha_service(req: CallServiceRequest):
    domain = req.domain or req.entity_id.split(".")[0]
    success = await ha_bridge.call_service(domain, req.service, req.entity_id, req.service_data)
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
# AI AGENT ROUTER & MULTI-MODEL MANAGEMENT APIS
# -----------------------------------------------------------------------------
class AITestRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

@app.get("/api/ai/config")
async def get_ai_config():
    """Lấy cấu hình AI hiện tại (API Key được che giấu an toàn)."""
    return JSONResponse(ai_router.get_safe_config())

@app.post("/api/ai/config")
async def save_ai_config(req: Request):
    """Lưu cấu hình AI mới (Provider, API Key, Model, Task Routing)."""
    try:
        data = await req.json()
        success = ai_router.save_config(data)
        if success:
            return JSONResponse({"status": "success", "message": "Đã lưu cấu hình AI Router thành công!"})
        else:
            return JSONResponse({"status": "error", "message": "Lưu cấu hình thất bại"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

@app.post("/api/ai/test")
async def test_ai_provider(req: AITestRequest):
    """Kiểm tra kết nối trực tiếp đến mô hình AI đã chọn và đo latency."""
    res = await ai_router.test_connection(req.provider, req.api_key, req.model, req.base_url)
    return JSONResponse(res)

# -----------------------------------------------------------------------------
# ALL-HOUSE MASTER CONFIGURATION & CONTROL APIS
# -----------------------------------------------------------------------------
@app.get("/api/all-house/config")
async def get_all_house_config_endpoint():
    """Lấy cấu hình nút Toàn Nhà & Tắt Hết kèm danh sách các Scenes có sẵn từ HA."""
    cfg = load_all_house_config()
    scenes = []
    for eid, obj in ha_bridge.states.items():
        if eid.startswith("scene."):
            friendly_name = obj.get("attributes", {}).get("friendly_name", eid)
            scenes.append({
                "entity_id": eid,
                "friendly_name": friendly_name
            })
    return JSONResponse({
        "config": cfg,
        "scenes": scenes,
        "house_status": get_house_status_summary()
    })

@app.post("/api/all-house/config")
async def update_all_house_config_endpoint(req: Request):
    """Lưu cấu hình mới cho nút Toàn Nhà & đồng bộ trạng thái mới tới toàn bộ màn hình."""
    try:
        data = await req.json()
        saved = save_all_house_config(data)
        if not saved:
            return JSONResponse({"status": "error", "message": "Failed to save configuration file"}, status_code=500)
        
        # Cập nhật và phát sóng trạng thái nhà mới nhất tới tất cả các màn hình ESP32 và Admin
        house_st = get_house_status_summary()
        for code_k, ws_k in list(active_sockets.items()):
            try:
                await ws_k.send_json({
                    "type": "house_status_update",
                    "payload": house_st
                })
            except Exception:
                pass
        
        return JSONResponse({
            "status": "success",
            "message": "Cấu hình nút Toàn Nhà đã được cập nhật thành công!",
            "house_status": house_st
        })
    except Exception as e:
        logger.error("Error updating all_house_config: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/all-house/master-off")
async def trigger_master_turn_off_endpoint():
    """Kích hoạt Tắt Hết Toàn Nhà từ Web Admin dựa theo cấu hình hiện hành."""
    try:
        cfg = load_all_house_config()
        res = await ha_bridge.master_turn_off_all(config=cfg)
        house_st = get_house_status_summary()
        floors_ov = get_floors_overview()
        for code_k, ws_k in list(active_sockets.items()):
            try:
                await ws_k.send_json({
                    "type": "house_status_update",
                    "payload": house_st,
                    "floors_overview": floors_ov
                })
            except Exception:
                pass
        return JSONResponse({
            "status": "success",
            "result": res,
            "house_status": house_st,
            "floors_overview": floors_ov
        })
    except Exception as e:
        logger.error("Error executing master-off API: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/all-house/floors-overview")
async def get_floors_overview_endpoint():
    """Lấy cây phân tầng và trạng thái phòng/thiết bị toàn nhà."""
    try:
        return JSONResponse({
            "status": "success",
            "overview": get_floors_overview(),
            "house_status": get_house_status_summary()
        })
    except Exception as e:
        logger.error("Error get_floors_overview_endpoint: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/all-house/turn-off-floor")
async def turn_off_floor_endpoint(request: Request):
    """Tắt toàn bộ thiết bị đang bật trong 1 tầng cụ thể (bảo vệ các thiết bị trong danh sách loại trừ)."""
    try:
        data = await request.json()
        floor_id = data.get("floor_id")
        cfg = load_all_house_config()
        excluded = set(cfg.get("excluded_entities", []))
        controlled_domains = set(cfg.get("controlled_domains", ["light", "fan"]))
        if cfg.get("include_climate", False): controlled_domains.add("climate")
        if cfg.get("include_switch", False): controlled_domains.add("switch")

        overview = get_floors_overview()
        turned_off = []
        for fl in overview["floors"]:
            if fl["floor_id"] == floor_id:
                for ar in fl["areas"]:
                    for e in ar["entities"]:
                        eid = e["entity_id"]
                        domain = e["domain"]
                        if eid in excluded:
                            continue
                        if domain not in controlled_domains:
                            continue
                        if e["is_on"]:
                            if domain == "climate":
                                await ha_bridge.call_service("climate", "set_hvac_mode", eid, {"hvac_mode": "off"})
                            else:
                                await ha_bridge.call_service(domain, "turn_off", eid)
                            turned_off.append(eid)
        
        # Broadcast trạng thái mới
        new_overview = get_floors_overview()
        house_st = get_house_status_summary()
        for code_k, ws_k in list(active_sockets.items()):
            try:
                await ws_k.send_json({
                    "type": "house_status_update",
                    "payload": house_st,
                    "floors_overview": new_overview
                })
            except Exception:
                pass
        logger.info("Turned off floor [%s], %d devices: %s", floor_id, len(turned_off), turned_off)
        return JSONResponse({
            "status": "success",
            "floor_id": floor_id,
            "turned_off_count": len(turned_off),
            "devices": turned_off,
            "floors_overview": new_overview,
            "house_status": house_st
        })
    except Exception as e:
        logger.error("Error turning off floor: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/all-house/turn-off-area")
async def turn_off_area_endpoint(request: Request):
    """Tắt toàn bộ thiết bị đang bật trong 1 phòng cụ thể (bảo vệ các thiết bị trong danh sách loại trừ)."""
    try:
        data = await request.json()
        area_id = data.get("area_id")
        cfg = load_all_house_config()
        excluded = set(cfg.get("excluded_entities", []))
        controlled_domains = set(cfg.get("controlled_domains", ["light", "fan"]))
        if cfg.get("include_climate", False): controlled_domains.add("climate")
        if cfg.get("include_switch", False): controlled_domains.add("switch")

        overview = get_floors_overview()
        turned_off = []
        for fl in overview["floors"]:
            for ar in fl["areas"]:
                if ar["area_id"] == area_id:
                    for e in ar["entities"]:
                        eid = e["entity_id"]
                        domain = e["domain"]
                        if eid in excluded:
                            continue
                        if domain not in controlled_domains:
                            continue
                        if e["is_on"]:
                            if domain == "climate":
                                await ha_bridge.call_service("climate", "set_hvac_mode", eid, {"hvac_mode": "off"})
                            else:
                                await ha_bridge.call_service(domain, "turn_off", eid)
                            turned_off.append(eid)
        
        new_overview = get_floors_overview()
        house_st = get_house_status_summary()
        for code_k, ws_k in list(active_sockets.items()):
            try:
                await ws_k.send_json({
                    "type": "house_status_update",
                    "payload": house_st,
                    "floors_overview": new_overview
                })
            except Exception:
                pass
        logger.info("Turned off area [%s], %d devices: %s", area_id, len(turned_off), turned_off)
        return JSONResponse({
            "status": "success",
            "area_id": area_id,
            "turned_off_count": len(turned_off),
            "devices": turned_off,
            "floors_overview": new_overview,
            "house_status": house_st
        })
    except Exception as e:
        logger.error("Error turning off area: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


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
    logger.info("New WebSocket connection: %s (Client: %s)", device_id, getattr(websocket.client, 'host', 'unknown') if hasattr(websocket, 'client') else 'unknown')

    dev_code: Optional[str] = None

    # Nếu kết nối là Web Admin Dashboard -> Gửi ngay toàn bộ dữ liệu khởi tạo
    if device_id.startswith("web_admin"):
        active_sockets[device_id] = websocket
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
                "history_settings": history_mgr.get_settings(),
                "house_status": get_house_status_summary(),
                "floors_overview": get_floors_overview()
            })
        except Exception as e:
            logger.error("Failed to send init to web_admin: %s", e)

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                logger.info("WebSocket disconnected for: %s", dev_code or device_id)
                break

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
                    fw_ver = payload.get("firmware_version", "v2.7.4")

                    if code:
                        dev_code = code
                        # Đóng socket cũ nếu có socket stale trước đó của code này
                        old_ws = active_sockets.get(code)
                        if old_ws and old_ws != websocket:
                            try:
                                await old_ws.close()
                            except Exception:
                                pass

                        active_sockets[code] = websocket
                        audio_record_buffers[code] = bytearray()
                        if code not in devices_db:
                            assigned_intercom_id = intercom.assign_id(code)
                            devices_db[code] = {
                                "device_id": f"panel_{code.lower()}",
                                "mac": mac,
                                "pairing_code": code,
                                "ip": ip,
                                "model": model,
                                "firmware_version": fw_ver,
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
                            if mac:
                                devices_db[code]["mac"] = mac
                            if fw_ver:
                                devices_db[code]["firmware_version"] = fw_ver
                            if "intercom_id" not in devices_db[code]:
                                devices_db[code]["intercom_id"] = intercom.assign_id(code)
                            save_devices()

                        dev = devices_db[code]
                        payload_st = payload.get("settings")
                        if payload_st and isinstance(payload_st, dict):
                            cur_st = dev.get("settings", {})
                            cur_st.update(payload_st)
                            dev["settings"] = cur_st
                            save_devices()

                        assigned_intercom_id = dev.get("intercom_id", 1)
                        intercom.register(code, websocket, assigned_intercom_id, meta={
                            "room_name": dev.get("room_name", f"Panel {code}"),
                            "floor": dev.get("floor", "")
                        })

                        # Tự động sync cấu hình đã lưu xuống Panel kèm kênh đàm thoại
                        targets = intercom.get_targets(exclude_device_key=code)
                        rname = dev.get("room_name", f"Panel {code}")
                        await websocket.send_json({
                            "type": "config_sync",
                            "payload": {
                                "room": f"{dev['room_name']} - {dev['floor']}",
                                "floor": dev['floor'],
                                "my_intercom_id": assigned_intercom_id,
                                "intercom_targets": targets,
                                "buttons": get_buttons_with_state(dev, include_all_house_active=False),
                                "all_rooms": get_all_rooms_summary(local_room=rname),
                                "house_status": get_house_status_summary(),
                                "entities": dev.get("entities", []),
                                "settings": dev.get("settings", {})
                            }
                        })
                        logger.info("Auto-synced existing configuration to Panel [%s] (Intercom ID: %d, Targets: %d)", code, assigned_intercom_id, len(targets))

                        # KHONG tu dong cuong buc OTA khi ket noi de tranh vong lap downgrade / freeze cam ung


                        logger.info("Panel [%s] connected with firmware %s (Auto-OTA disabled)", code, fw_ver)

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
                    action = payload.get("action", "")
                    if action == "master_turn_off_all" or payload.get("service") == "master_turn_off_all":
                        logger.info("Received master_turn_off_all from %s", dev_code)
                        cfg = load_all_house_config()
                        turned_off = await ha_bridge.master_turn_off_all(config=cfg)
                        house_st = get_house_status_summary()
                        for code_k, ws_k in list(active_sockets.items()):
                            try:
                                await ws_k.send_json({
                                    "type": "house_status_update",
                                    "payload": house_st
                                })
                            except Exception:
                                pass
                    else:
                        entity_id = payload.get("entity_id", "")
                        domain = payload.get("domain") or (entity_id.split(".")[0] if "." in entity_id else "light")
                        service = payload.get("service", "toggle")
                        service_data = payload.get("service_data")
                        if entity_id:
                            if domain == "climate" and service == "toggle":
                                cur_st = ha_bridge.states.get(entity_id, {}).get("state", "off")
                                target_mode = "off" if cur_st not in ["off", "unavailable", "unknown", ""] else "cool"
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
                                    entity_id=entity_id,
                                    service_data=service_data
                                )

                # Đồng bộ cập nhật cài đặt từ Panel lên Server và Web Admin
                elif msg_type == "settings_update":
                    payload = data.get("payload", {})
                    st = payload.get("settings", {})
                    if dev_code and dev_code in devices_db:
                        dev = devices_db[dev_code]
                        cur_st = dev.get("settings", {})
                        cur_st.update(st)
                        dev["settings"] = cur_st
                        save_devices()
                        logger.info("Updated settings from Panel [%s]: %s", dev_code, st)
                        await broadcast_to_admins({
                            "type": "devices_update",
                            "devices": get_devices_list(),
                            "intercom_targets": intercom.get_targets()
                        })

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
                            target_mode = "off" if cur_st not in ["off", "unavailable", "unknown", ""] else "cool"
                            await ha_bridge.call_service(domain="climate", service="set_hvac_mode", entity_id=entity_id, service_data={"hvac_mode": target_mode})
                        else:
                            await ha_bridge.call_service(domain=domain, service="toggle", entity_id=entity_id)
                    elif action == "entity_climate_temp":
                        entity_id = data.get("entity_id", "")
                        temp = data.get("temperature", 26.0)
                        await ha_bridge.call_service(domain="climate", service="set_temperature", entity_id=entity_id, service_data={"temperature": float(temp)})
                    elif action == "entity_climate_mode":
                        entity_id = data.get("entity_id", "")
                        mode = data.get("hvac_mode", "cool")
                        await ha_bridge.call_service(domain="climate", service="set_hvac_mode", entity_id=entity_id, service_data={"hvac_mode": mode})
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
                                        "buttons": get_buttons_with_state(dev, include_all_house_active=False),
                                        "all_rooms": get_all_rooms_summary(local_room=dev.get("room_name", "")),
                                        "house_status": get_house_status_summary(),
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
        intercom.unregister(current_key, websocket)
        if device_id.startswith("web_admin"):
            intercom.unregister_admin(websocket)
            if active_sockets.get(device_id) == websocket:
                del active_sockets[device_id]
        if dev_code:
            intercom.unregister(dev_code, websocket)
            if active_sockets.get(dev_code) == websocket:
                del active_sockets[dev_code]
            if dev_code in audio_record_buffers:
                del audio_record_buffers[dev_code]
            if dev_code in devices_db and active_sockets.get(dev_code) is None:
                devices_db[dev_code]["online"] = False
                logger.info("Device [%s] disconnected -> marked OFFLINE", dev_code)

        if active_sockets.get(device_id) == websocket:
            del active_sockets[device_id]

        # Cập nhật danh sách thiết bị cho Admin khi có thiết bị ngắt kết nối
        if dev_code or not device_id.startswith("web_admin"):
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
