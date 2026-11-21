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
import io
import wave
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse, StreamingResponse, Response
from pydantic import BaseModel
import uvicorn

# Force Vietnam Timezone (Asia/Ho_Chi_Minh - GMT+7) across all platforms & Docker
if "TZ" not in os.environ:
    os.environ["TZ"] = "Asia/Ho_Chi_Minh"
if hasattr(time, "tzset"):
    time.tzset()

try:
    import opuslib
    OPUS_AVAILABLE = True
except Exception as _opus_err:
    opuslib = None
    OPUS_AVAILABLE = False

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
from app.stt_tts_pipeline import AudioPipeline, DEFAULT_SMART_HOME_WHISPER_PROMPT
from app.ai_agent_router import AIAgentRouter, _normalize_vn
from app.wake_word_manager import WakeWordManager
from app.history_manager import HistoryManager
try:
    from app.voiceprint_manager import voiceprintManager
except ImportError:
    from voiceprint_manager import voiceprintManager

try:
    from app.living_context_engine import livingContextEngine
except ImportError:
    from living_context_engine import livingContextEngine

try:
    from app.automation_engine import automationEngine
except ImportError:
    from automation_engine import automationEngine

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
STT_URL = os.getenv("STT_SERVICE_URL", "http://127.0.0.1:8095/v1/audio/transcriptions")
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
if hasattr(ai_router, 'config'):
    audio_pipeline.set_voice_settings(
        voice=ai_router.config.get("tts_voice"),
        rate=ai_router.config.get("tts_rate", "+0%"),
        pitch=ai_router.config.get("tts_pitch", "+0Hz")
    )
history_mgr = HistoryManager()
if automationEngine:
    automationEngine.ha_bridge = ha_bridge
if livingContextEngine:
    livingContextEngine.ha_bridge = ha_bridge

async def send_audio_chunks(ws: WebSocket, pcm_data: bytes, is_opus: bool, start_seq: int = 0, encoder: Any = None) -> int:
    """Helper gửi các chunk âm thanh (Opus hoặc PCM) qua WebSocket."""
    seq = start_seq
    tot = len(pcm_data)
    if is_opus and OPUS_AVAILABLE:
        enc = encoder or opuslib.Encoder(16000, 1, 'voip')
        for i in range(0, tot, 640):
            c = pcm_data[i:i+640]
            if len(c) < 640:
                c = c + b'\x00' * (640 - len(c))
            try:
                enc_payload = enc.encode(c, 320)
                enc_len = len(enc_payload)
                flag = 0x01 if seq == 0 else 0x02
                hdr = bytearray(9)
                hdr[0:2] = (0xA55B).to_bytes(2, 'little')
                hdr[2] = 0x00 # Server Hub
                hdr[3] = 0x01 # ESP32 Panel
                hdr[4:6] = seq.to_bytes(2, 'little')
                hdr[6] = flag
                hdr[7:9] = enc_len.to_bytes(2, 'little')
                await ws.send_bytes(bytes(hdr + enc_payload))
                seq += 1
                await asyncio.sleep(0.016)
            except Exception as e:
                logger.error("Lỗi encode frame Opus: %s", e)
    else:
        for i in range(0, tot, 512):
            c = pcm_data[i:i+512]
            if len(c) < 512:
                c = c + b'\x00' * (512 - len(c))
            flag = 0x01 if seq == 0 else 0x02
            hdr = bytearray(7)
            hdr[0:2] = (0xA55A).to_bytes(2, 'little')
            hdr[2] = 0x00 # Server Hub
            hdr[3] = 0x01 # ESP32
            hdr[4:6] = seq.to_bytes(2, 'little')
            hdr[6] = flag
            await ws.send_bytes(bytes(hdr + c + b'\x00'))
            seq += 1
            await asyncio.sleep(0.012)
    return seq

async def send_audio_end(ws: WebSocket, is_opus: bool, seq: int):
    """Gửi frame kết thúc phát âm thanh (STREAM_FLAG_END = 0x03)."""
    if is_opus and OPUS_AVAILABLE:
        end_hdr = bytearray(9)
        end_hdr[0:2] = (0xA55B).to_bytes(2, 'little')
        end_hdr[2] = 0x00
        end_hdr[3] = 0x01
        end_hdr[4:6] = seq.to_bytes(2, 'little')
        end_hdr[6] = 0x03
        end_hdr[7:9] = (0).to_bytes(2, 'little')
        await ws.send_bytes(bytes(end_hdr))
    else:
        end_hdr = bytearray(7)
        end_hdr[0:2] = (0xA55A).to_bytes(2, 'little')
        end_hdr[2] = 0x00
        end_hdr[3] = 0x01
        end_hdr[4:6] = seq.to_bytes(2, 'little')
        end_hdr[6] = 0x03
        await ws.send_bytes(bytes(end_hdr + b'\x00' * 513))

# Quản lý task AI thoại thời gian thực cho tính năng Cắt Lời Tức Thì (Barge-in / Abort Speaking)
active_ai_tasks: Dict[str, asyncio.Task] = {}
opus_decoders: Dict[str, Any] = {}
client_audio_formats: Dict[str, str] = {}

async def abort_ai_flow(device_id: str, ws: Optional[WebSocket] = None):
    """Hủy tức thì tác vụ AI đang sinh câu trả lời hoặc stream audio xuống thiết bị (Barge-in)."""
    task = active_ai_tasks.get(device_id)
    if task and not task.done():
        logger.info("[BARGE-IN] Cắt lời AI tức thì cho thiết bị [%s]!", device_id)
        task.cancel()
    active_ai_tasks.pop(device_id, None)
    target_ws = ws or active_sockets.get(device_id)
    if target_ws:
        try:
            await target_ws.send_json({"type": "tts_stop"})
            await target_ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
        except Exception:
            pass

async def on_wake_winner(device_id: str, candidate_info: dict):
    ws = active_sockets.get(device_id)
    # Khóa cooldown ngay lập tức để không thể kích hoạt lặp lại trong 4 giây
    wake_mgr.set_cooldown(device_id, duration_sec=4.0)
    # Cắt lời AI nếu đang phát âm thanh cũ khi người dùng gọi từ khóa Wake Word mới
    await abort_ai_flow(device_id, ws)
    dev_info = devices_db.get(device_id, {})
    room_name = dev_info.get("room_name", f"Panel {device_id}")
    tts_voice = ai_router.config.get("tts_voice", "google_fast")
    if ws:
        try:
            # Gửi lệnh wake_trigger đến ESP32 chiến thắng kèm phản hồi câu thoại Xiaozhi
            await ws.send_json({
                "type": "wake_trigger",
                "source": "wake_word",
                "model": candidate_info.get("model", "hey_nala"),
                "score": candidate_info.get("score", 1.0),
                "room": room_name,
                "text": "Em nghe!"
            })
            # Phát âm thanh phản hồi "Em nghe!" tức thì từ RAM cache (<1ms) như XiaoZhi
            greeting_pcm = await audio_pipeline.text_to_pcm("Em nghe!", voice=tts_voice)
            if greeting_pcm:
                logger.info("[WAKE] Gửi âm thanh chào 'Em nghe!' (%d bytes) đến panel [%s]", len(greeting_pcm), device_id)
                is_opus = (client_audio_formats.get(device_id) == "opus") and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                last_seq = await send_audio_chunks(ws, greeting_pcm, is_opus=is_opus, start_seq=0)
                await send_audio_end(ws, is_opus=is_opus, seq=last_seq)
            else:
                logger.warning("[WAKE] greeting_pcm rỗng, không thể phát chào cho [%s]!", device_id)
        except Exception as e:
            logger.error("Error sending wake_trigger / greeting to %s: %s", device_id, e)

    asyncio.create_task(broadcast_to_admins({
        "type": "wake_notification",
        "device_id": device_id,
        "room_name": room_name,
        "score": candidate_info.get("score", 1.0),
        "rms": candidate_info.get("rms", 0.0)
    }))

async def on_wake_suppressed(device_id: str, candidate_info: dict):
    ws = active_sockets.get(device_id)
    if ws:
        try:
            await ws.send_json({
                "type": "wake_suppress",
                "duration_ms": 2000
            })
            await ws.send_json({
                "type": "wake_event",
                "payload": {
                    "status": "suppressed"
                }
            })
        except Exception:
            pass

async def on_wake_score_tick(device_id: str, model: str, score: float, rms: float, threshold: float):
    # Chỉ broadcast nếu là web_admin test HOẶC có âm thanh/score đáng chú ý để tránh tràn kênh
    if device_id.startswith("web_admin") or score >= 0.05 or rms > -45.0:
        room_name = "Micro Máy Tính (PC Browser)" if device_id.startswith("web_admin") else devices_db.get(device_id, {}).get("room_name", f"Panel {device_id}")
        await broadcast_to_admins({
            "type": "wake_score_tick",
            "device_id": device_id,
            "room_name": room_name,
            "model": model,
            "score": round(score, 4),
            "score_pct": int(round(score * 100)),
            "rms": round(rms, 1),
            "threshold": round(threshold, 2),
            "is_wake": score >= threshold
        })

async def on_wake_detected(device_id: str, model: str, score: float, rms: float, threshold: float):
    room_name = "Micro Máy Tính (PC Browser)" if device_id.startswith("web_admin") else devices_db.get(device_id, {}).get("room_name", f"Panel {device_id}")
    await broadcast_to_admins({
        "type": "wake_detected",
        "device_id": device_id,
        "room_name": room_name,
        "model": model,
        "score": round(score, 4),
        "score_pct": int(round(score * 100)),
        "rms": round(rms, 1),
        "threshold": round(threshold, 2)
    })

wake_mgr = WakeWordManager(
    on_winner_callback=on_wake_winner, 
    on_suppress_callback=on_wake_suppressed,
    on_score_tick_callback=on_wake_score_tick,
    on_detect_callback=on_wake_detected
)

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
            if len(buttons_with_state) >= 6:
                continue
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

            if len(room_buttons) >= 6:
                continue
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
            if len(room_buttons) >= 6:
                continue
            room_buttons.append({
                "id": f"ha_{eid.replace('.', '_')}",
                "name": dname[:14],
                "entity_id": eid,
                "icon": item["domain"],
                "is_on": item["is_on"],
                "state": item["state"]
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
    return rooms[:8]

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

async def broadcast_to_panels(msg: dict):
    """Gửi thông điệp thời gian thực tới tất cả màn hình ESP32 đang kết nối."""
    for dev_id, ws in list(active_sockets.items()):
        if not dev_id.startswith("web_admin"):
            try:
                await ws.send_json(msg)
            except Exception:
                pass

def get_wake_model_label(m_name: str) -> str:
    """Chuyển đổi mã model sang tên hiển thị thân thiện tiếng Việt/tiếng Anh trên ESP32."""
    if not m_name:
        return "Hey Nala"
    if m_name == "hey_nala":
        return "Hey Nala"
    elif m_name == "nala_oi":
        return "Nala Ơi"
    elif m_name == "hey_jarvis":
        return "Hey Jarvis"
    elif m_name == "alexa":
        return "Alexa"
    return m_name.replace("_", " ").title()

def get_available_wake_models() -> list:
    """Lấy danh sách các model Wake Word có sẵn (.onnx hoặc built-in), trừ các model đã ẩn."""
    base_models = ["nala_oiv1", "hey_nala", "nala_oi", "hey_jarvis", "alexa"]
    hidden_models = set(wake_mgr.config.get("hidden_models", []))
    available_models = [m for m in base_models if m not in hidden_models]
    custom_models_dir = os.path.join(wake_mgr.data_dir, "models")
    if os.path.exists(custom_models_dir):
        for fname in os.listdir(custom_models_dir):
            if fname.endswith(".onnx") or fname.endswith(".tflite"):
                m_name = os.path.splitext(fname)[0]
                if m_name not in available_models and m_name not in hidden_models:
                    available_models.append(m_name)
    return available_models

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

    # Attributes tinh gọn cho màn hình ESP32 (chỉ lấy các trường cần hiển thị trên UI)
    safe_attrs = {}
    for k in ["temperature", "current_temperature", "hvac_mode", "fan_mode", "swing_mode", "friendly_name"]:
        if k in attrs:
            safe_attrs[k] = attrs[k]

    panel_msg = {
        "type": "ha_state_change",
        "payload": {
            "entity_id": entity_id,
            "state": new_state,
            "is_on": is_on,
            "attributes": safe_attrs,
            "house_status": house_status
        }
    }

    for dev_id, ws in list(active_sockets.items()):
        try:
            if dev_id.startswith("web_admin"):
                await ws.send_json(base_msg)
            else:
                await ws.send_json(panel_msg)
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
                    intercom.unregister(code)
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

async def time_sync_periodic_task():
    """Periodically sync real-time clock down to all connected ESP32 panels every 30 minutes."""
    while True:
        try:
            await asyncio.sleep(1800)  # Mỗi 30 phút tự động đồng bộ giờ
            cur_epoch = int(time.time())
            await broadcast_to_panels({
                "type": "time_sync",
                "epoch": cur_epoch
            })
            logger.info("Periodic time_sync broadcasted to panels: epoch %d (%s)", cur_epoch, time.strftime("%Y-%m-%d %H:%M:%S %Z"))
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Error in time_sync_periodic_task: %s", e)
            await asyncio.sleep(60)

async def handle_intercom_silence_warning(session: dict):
    """Phát cảnh báo im lặng 10s (đếm ngược 3s) tới 2 bên màn hình."""
    caller_k = session.get("caller_key")
    target_k = session.get("target_key")
    warn_msg = {
        "type": "intercom_silence_warning",
        "countdown": 3,
        "session_id": session.get("session_id")
    }
    for k in (caller_k, target_k):
        ws = active_sockets.get(k)
        if ws:
            try:
                await ws.send_json(warn_msg)
            except Exception:
                pass

async def handle_intercom_silence_hangup(session: dict, reason: str):
    """Cúp máy do im lặng 13s, thông báo tới 2 bên màn hình và Web Admin."""
    caller_k = session.get("caller_key")
    target_k = session.get("target_key")
    hangup_msg = {
        "type": "intercom_hangup",
        "reason": reason,
        "session_id": session.get("session_id")
    }
    for k in (caller_k, target_k):
        ws = active_sockets.get(k)
        if ws:
            try:
                await ws.send_json(hangup_msg)
            except Exception:
                pass
    await broadcast_to_admins({
        "type": "intercom_active_calls",
        "calls": intercom.get_active_calls_summary()
    })

async def intercom_silence_watchdog_task():
    """Kiểm tra thời gian im lặng định kỳ 1 giây/lần cho đàm thoại rảnh tay (Silence Watchdog 10s)."""
    while True:
        try:
            await asyncio.sleep(1.0)
            if intercom.active_handsfree_sessions:
                await intercom.check_silence_watchdogs(
                    on_warning_cb=handle_intercom_silence_warning,
                    on_hangup_cb=handle_intercom_silence_hangup
                )
        except asyncio.CancelledError:
            break
        except Exception as ex:
            logger.warning("Error in intercom silence watchdog: %s", ex)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting NALA Central Hub on port %d...", PORT)
    load_devices()
    ha_bridge.add_state_listener(on_ha_state_change)
    asyncio.create_task(ha_bridge.connect())
    asyncio.create_task(audio_pipeline.prewarm_common_cache())
    asyncio.create_task(history_cleanup_task())
    asyncio.create_task(device_heartbeat_task())
    asyncio.create_task(time_sync_periodic_task())
    asyncio.create_task(intercom_silence_watchdog_task())

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

@app.post("/api/time/sync")
async def trigger_time_sync():
    """Manually trigger RTC time synchronization to all connected ESP32 panels and Web Admins."""
    cur_epoch = int(time.time())
    local_str = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    
    panel_count = 0
    for dev_id, ws in list(active_sockets.items()):
        if not dev_id.startswith("web_admin"):
            try:
                await ws.send_json({
                    "type": "time_sync",
                    "epoch": cur_epoch
                })
                panel_count += 1
            except Exception:
                pass

    await broadcast_to_admins({
        "type": "time_synced",
        "epoch": cur_epoch,
        "local_time": local_str,
        "panels_synced": panel_count
    })

    logger.info("Manual time_sync triggered: epoch=%d (%s), synced %d panels", cur_epoch, local_str, panel_count)
    return {
        "status": "ok",
        "epoch": cur_epoch,
        "local_time": local_str,
        "panels_synced": panel_count,
        "timezone": os.environ.get("TZ", "Asia/Ho_Chi_Minh")
    }

@app.get("/api/time/status")
async def get_time_status():
    """Get current server time and timezone status."""
    cur_epoch = int(time.time())
    return {
        "epoch": cur_epoch,
        "local_time": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "timezone": os.environ.get("TZ", "Asia/Ho_Chi_Minh"),
        "is_dst": bool(time.localtime().tm_isdst)
    }

@app.get("/api/intercom/targets")
async def get_intercom_targets_api():
    """Lấy danh sách các kênh Intercom có sẵn và trạng thái online."""
    return {
        "status": "ok",
        "targets": intercom.get_targets()
    }

@app.get("/api/intercom/active_calls")
async def get_active_intercom_calls_api():
    """Lấy danh sách các cuộc gọi đàm thoại rảnh tay đang diễn ra."""
    return {
        "status": "ok",
        "active_calls": intercom.get_active_calls_summary()
    }

class IntercomCallRequest(BaseModel):
    caller_key: str
    target_key: str

@app.post("/api/intercom/call")
async def start_intercom_call_api(req: IntercomCallRequest):
    """Bắt đầu cuộc gọi đàm thoại rảnh tay giữa 2 màn hình từ Web Admin."""
    caller_k = req.caller_key.strip().upper()
    target_k = req.target_key.strip().upper()
    caller_ws = intercom.connections.get(caller_k) or active_sockets.get(caller_k)
    target_ws = intercom.connections.get(target_k) or active_sockets.get(target_k)

    if not target_ws:
        return {"status": "error", "message": f"Màn hình phòng đích [{target_k}] đang ngoại tuyến."}

    sess = intercom.start_handsfree_call(caller_k, target_k)
    if caller_ws:
        try:
            await caller_ws.send_json({
                "type": "intercom_call_started",
                "role": "caller",
                "target_room": sess["target_room"],
                "target_code": target_k,
                "session_id": sess["session_id"]
            })
        except Exception:
            pass

    try:
        await target_ws.send_json({
            "type": "intercom_incoming_call",
            "role": "callee",
            "caller_room": sess["caller_room"],
            "caller_code": caller_k,
            "auto_answer": True,
            "session_id": sess["session_id"]
        })
    except Exception:
        pass

    await broadcast_to_admins({
        "type": "intercom_active_calls",
        "calls": intercom.get_active_calls_summary()
    })
    return {"status": "ok", "session": sess}

class IntercomHangupRequest(BaseModel):
    device_key: Optional[str] = None
    session_id: Optional[str] = None

@app.post("/api/intercom/hangup")
async def hangup_intercom_call_api(req: IntercomHangupRequest):
    """Cúp máy cuộc gọi đàm thoại rảnh tay từ xa."""
    dev_key = (req.device_key or "").strip().upper()
    sess = None
    if dev_key:
        sess = intercom.end_handsfree_call(dev_key, reason="admin_hangup")
    elif req.session_id:
        for k, s in list(intercom.active_handsfree_sessions.items()):
            if s.get("session_id") == req.session_id:
                sess = intercom.end_handsfree_call(k, reason="admin_hangup")
                break

    if sess:
        hangup_payload = {"type": "intercom_hangup", "reason": "admin_hangup", "session_id": sess.get("session_id")}
        for k in (sess.get("caller_key"), sess.get("target_key")):
            k_ws = active_sockets.get(k)
            if k_ws:
                try:
                    await k_ws.send_json(hangup_payload)
                except Exception:
                    pass
        await broadcast_to_admins({
            "type": "intercom_active_calls",
            "calls": intercom.get_active_calls_summary()
        })
        return {"status": "ok", "message": "Đã ngắt cuộc gọi."}

    return {"status": "error", "message": "Không tìm thấy cuộc gọi đang hoạt động."}

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

    if req.action == "wake":
        await on_wake_winner(code, {"model": "hey_nala", "score": 1.0})
        logger.info("Manual wake action triggered for [%s]", code)
        return JSONResponse({"status": "success", "message": f"Triggered wake for [{code}]"})

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
    """Lưu cấu hình AI mới (Provider, API Key, Model, Task Routing, Voice Persona, Rate, Pitch)."""
    try:
        data = await req.json()
        success = ai_router.save_config(data)
        if success:
            audio_pipeline.set_voice_settings(
                voice=data.get("tts_voice"),
                rate=data.get("tts_rate"),
                pitch=data.get("tts_pitch")
            )
            return JSONResponse({"status": "success", "message": "Đã lưu cấu hình AI & Vai trò giọng nói thành công!"})
        else:
            return JSONResponse({"status": "error", "message": "Lưu cấu hình thất bại"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

class TTSPreviewRequest(BaseModel):
    text: Optional[str] = "Xin chào! Mình là Nala, trợ lý nhà thông minh của bạn."
    voice: Optional[str] = "vi-VN-HoaiMyNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"

@app.post("/api/tts/preview")
async def tts_preview(req: TTSPreviewRequest):
    """Tạo audio preview MP3/WAV trực tiếp cho trình duyệt nghe thử (XiaoZhi style)."""
    text = (req.text or "").strip() or "Xin chào! Mình là Nala, trợ lý nhà thông minh của bạn."
    voice = req.voice or "vi-VN-HoaiMyNeural"
    rate = req.rate or "+0%"
    pitch = req.pitch or "+0Hz"

    if voice in ("google_fast", "google", "fast") or voice.startswith("google"):
        pcm = await audio_pipeline.google_tts_to_pcm(text)
        if pcm:
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm)
            return Response(content=wav_buf.getvalue(), media_type="audio/wav")
    else:
        # 1. Thử qua Edge-TTS với rate & pitch tùy chỉnh
        try:
            import edge_tts
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            if buf:
                return Response(content=bytes(buf), media_type="audio/mpeg")
        except Exception as e:
            logger.warning("Edge-TTS preview error (%s): %s", voice, e)

        # 2. Thử lại Edge-TTS mặc định (không rate/pitch) phòng khi thông số bị server từ chối
        try:
            import edge_tts
            comm = edge_tts.Communicate(text, voice)
            buf = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    buf.extend(chunk["data"])
            if buf:
                return Response(content=bytes(buf), media_type="audio/mpeg")
        except Exception as e:
            logger.warning("Edge-TTS default preview error (%s): %s", voice, e)

        # 3. Fallback tức thì qua Google Fast TTS (WAV 16kHz)
        try:
            pcm = await audio_pipeline.google_tts_to_pcm(text)
            if pcm:
                wav_buf = io.BytesIO()
                with wave.open(wav_buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm)
                return Response(content=wav_buf.getvalue(), media_type="audio/wav")
        except Exception as e:
            logger.error("Google TTS preview error: %s", e)

    return JSONResponse({"status": "error", "message": "Không thể tạo âm thanh nghe thử"}, status_code=500)

@app.post("/api/ai/test")
async def test_ai_provider(req: AITestRequest):
    """Kiểm tra kết nối trực tiếp đến mô hình AI đã chọn và đo latency."""
    res = await ai_router.test_connection(req.provider, req.api_key, req.model, req.base_url)
    return JSONResponse(res)

class AIModelsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None

@app.post("/api/ai/models")
async def get_ai_models(req: AIModelsRequest):
    """Lấy danh sách các model khả dụng trực tiếp từ API của từng hãng."""
    models = await ai_router.list_available_models(req.provider, req.api_key, req.base_url)
    return JSONResponse({"status": "success", "provider": req.provider, "models": models})

class WeatherTestRequest(BaseModel):
    location: Optional[str] = "Hà Nội"

@app.post("/api/extensions/test_weather")
async def test_weather_endpoint(req: WeatherTestRequest):
    """Test trực tiếp dịch vụ thời tiết Open-Meteo."""
    loc = (req.location or "Hà Nội").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.get_weather(loc)
        return JSONResponse({"status": "success", "result": res})
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

class SearchTestRequest(BaseModel):
    query: str

@app.post("/api/extensions/test_search")
async def test_search_endpoint(req: SearchTestRequest):
    """Test trực tiếp tìm kiếm DuckDuckGo / Wikipedia."""
    q = (req.query or "").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.web_search(q)
        return JSONResponse({"status": "success", "result": res})
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

class MCPTestRequest(BaseModel):
    endpoint_url: str

@app.post("/api/extensions/test_mcp")
async def test_mcp_endpoint(req: MCPTestRequest):
    """Test kết nối và quét tools từ MCP Server endpoint."""
    url = (req.endpoint_url or "").strip()
    if hasattr(ai_router, "extension_service"):
        res = await ai_router.extension_service.test_mcp_server(url)
        return JSONResponse(res)
    return JSONResponse({"status": "error", "message": "Extension service chưa khởi tạo"}, status_code=500)

@app.get("/api/extensions/media_players")
async def get_media_players():
    """Lấy danh sách các loa / Media Player từ Home Assistant."""
    players = []
    if ha_bridge and hasattr(ha_bridge, "entities") and ha_bridge.entities:
        for eid, data in ha_bridge.entities.items():
            if eid.startswith("media_player."):
                f_name = data.get("attributes", {}).get("friendly_name", eid)
                state = data.get("state", "idle")
                players.append({"entity_id": eid, "friendly_name": f_name, "state": state})
    return JSONResponse({"status": "success", "players": players})

class AIChatRequest(BaseModel):
    message: str
    provider: Optional[str] = None

@app.get("/api/wake/config")
async def get_wake_config():
    """Lấy cấu hình Wake Word đa phòng hiện tại và danh sách mô hình có sẵn."""
    cfg = dict(wake_mgr.config)
    cfg["available_models"] = get_available_wake_models()

    # Quét danh sách mô hình có file vật lý trong data/models (.onnx, .tflite)
    custom_models_dir = os.path.join(wake_mgr.data_dir, "models")
    custom_models = []
    if os.path.exists(custom_models_dir):
        for fname in os.listdir(custom_models_dir):
            if fname.endswith(".onnx") or fname.endswith(".tflite"):
                custom_models.append(os.path.splitext(fname)[0])
    cfg["custom_models"] = custom_models

    # Gộp danh sách devices để hiển thị từng phòng trên Web Admin
    devices_summary = []
    for code, dev in devices_db.items():
        panel_cfg = cfg.get("panel_settings", {}).get(code, {})
        devices_summary.append({
            "device_code": code,
            "room_name": dev.get("room_name", f"Panel {code}"),
            "online": active_sockets.get(code) is not None,
            "wake_enabled": panel_cfg.get("wake_enabled", True),
            "sensitivity": panel_cfg.get("sensitivity", cfg.get("threshold", 0.5))
        })
    cfg["panels_list"] = devices_summary
    return JSONResponse(cfg)

@app.post("/api/wake/upload")
async def upload_wake_model(request: Request):
    """Tải lên mô hình Wake Word tùy biến (.tflite hoặc .onnx) dạng Base64 JSON."""
    try:
        data = await request.json()
        filename = data.get("filename", "hey_nala.onnx")
        b64_content = data.get("content_base64", "")
        if not (filename.endswith(".tflite") or filename.endswith(".onnx")):
            return JSONResponse({"status": "error", "message": "Chỉ chấp nhận file định dạng .tflite hoặc .onnx"}, status_code=400)
        import base64
        file_bytes = base64.b64decode(b64_content)
        custom_models_dir = os.path.join(wake_mgr.data_dir, "models")
        os.makedirs(custom_models_dir, exist_ok=True)
        dest_path = os.path.join(custom_models_dir, filename)
        with open(dest_path, "wb") as f:
            f.write(file_bytes)
        model_name = os.path.splitext(filename)[0]

        # Khôi phục nếu trước đó model này từng bị ẩn
        hidden_models = list(wake_mgr.config.get("hidden_models", []))
        if model_name in hidden_models:
            hidden_models.remove(model_name)
            wake_mgr.save_config({"hidden_models": hidden_models})

        wake_mgr.save_config({"selected_model": model_name})
        wake_mgr._init_model()

        # Broadcast đồng bộ tên Wake Word mới tới toàn bộ màn hình ESP32 và Web Admin
        wake_label = get_wake_model_label(model_name)
        await broadcast_to_panels({
            "type": "wake_config_update",
            "payload": {
                "wake_word": wake_label,
                "model": model_name
            }
        })
        await broadcast_to_admins({
            "type": "wake_config_update",
            "payload": {
                "selected_model": model_name,
                "available_models": get_available_wake_models()
            }
        })

        return JSONResponse({
            "status": "success",
            "message": f"Đã nạp thành công mô hình Wake Word '{model_name}'!",
            "model_name": model_name
        })
    except Exception as e:
        logger.error("Lỗi upload mô hình wake word: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/wake/delete")
@app.delete("/api/wake/model")
async def delete_wake_model(request: Request):
    """Xóa mô hình Wake Word khỏi máy chủ (xóa file .onnx / .tflite và giải phóng RAM)."""
    try:
        data = await request.json()
        model_name = data.get("model_name", "").strip()
        if not model_name:
            return JSONResponse({"status": "error", "message": "Tên mô hình không hợp lệ"}, status_code=400)

        custom_models_dir = os.path.join(wake_mgr.data_dir, "models")
        deleted_file = False
        if os.path.exists(custom_models_dir):
            for fname in os.listdir(custom_models_dir):
                base, ext = os.path.splitext(fname)
                if ext.lower() in [".onnx", ".tflite"] and base.lower() == model_name.lower():
                    file_path = os.path.join(custom_models_dir, fname)
                    try:
                        os.remove(file_path)
                        deleted_file = True
                        logger.info("Deleted custom wake word model file: %s", file_path)
                    except Exception as fe:
                        logger.error("Failed to delete file %s: %s", file_path, fe)
                        return JSONResponse({"status": "error", "message": f"Không thể xóa file: {fe}"}, status_code=500)

        # Cập nhật danh sách selected_models & hidden_models trong wake_config
        selected_models = list(wake_mgr.config.get("selected_models", []))
        if model_name in selected_models:
            selected_models.remove(model_name)

        hidden_models = list(wake_mgr.config.get("hidden_models", []))
        if model_name not in hidden_models:
            hidden_models.append(model_name)

        new_selected = selected_models if selected_models else ["nala_oiv1"]
        wake_mgr.save_config({
            "selected_models": new_selected,
            "hidden_models": hidden_models
        })

        # Nạp lại mô hình trong RAM để giải phóng bộ nhớ ngay lập tức
        wake_mgr._init_model()

        avail = get_available_wake_models()
        # Broadcast đồng bộ tới Web Admin
        await broadcast_to_admins({
            "type": "wake_config_update",
            "payload": {
                "deleted_model": model_name,
                "selected_models": new_selected,
                "available_models": avail
            }
        })

        msg = f"Đã xóa vĩnh viễn file mô hình '{model_name}' và giải phóng RAM!" if deleted_file else f"Đã gỡ mô hình '{model_name}' khỏi danh sách áp dụng!"
        return JSONResponse({
            "status": "success",
            "message": msg,
            "model_name": model_name,
            "available_models": avail,
            "selected_models": new_selected
        })
    except Exception as e:
        logger.error("Lỗi khi xóa mô hình wake word: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/wake/config")
async def save_wake_config(req: Request):
    """Lưu cấu hình Wake Word đa phòng và độ nhạy."""
    try:
        data = await req.json()
        saved = wake_mgr.save_config(data)
        if saved:
            new_model = wake_mgr.config.get("selected_model", "hey_nala")
            wake_label = get_wake_model_label(new_model)
            await broadcast_to_panels({
                "type": "wake_config_update",
                "payload": {
                    "wake_word": wake_label,
                    "model": new_model
                }
            })
            await broadcast_to_admins({
                "type": "wake_config_update",
                "payload": {
                    "selected_model": new_model,
                    "available_models": get_available_wake_models()
                }
            })
            return JSONResponse({"status": "success", "message": "Đã lưu cấu hình Wake Word thành công!"})
        return JSONResponse({"status": "error", "message": "Lưu cấu hình thất bại"}, status_code=500)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)

@app.post("/api/ai/chat")
async def ai_chat_endpoint(req: AIChatRequest):
    """Gửi tin nhắn test AI từ Web Admin và nhận câu trả lời cùng audio base64 để nghe thử trực tiếp trên trình duyệt."""
    try:
        reply = await ai_router.process_intent(req.message, model_preference=req.provider, device_id="web_admin")
        voice = ai_router.config.get("tts_voice", "vi-VN-HoaiMyNeural")
        pcm = await audio_pipeline.text_to_pcm(reply, voice=voice)
        wav_b64 = ""
        if pcm:
            import io, wave, base64
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(pcm)
            wav_b64 = base64.b64encode(wav_buf.getvalue()).decode('ascii')
        return JSONResponse({
            "status": "success",
            "reply": reply,
            "voice": voice,
            "audio_wav_base64": wav_b64
        })
    except Exception as e:
        logger.error("Error in ai_chat_endpoint: %s", e)
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/ai/context/clear")
async def clear_ai_context(req: Request):
    """Xóa bộ nhớ ngữ cảnh hội thoại đa lượt của thiết bị hoặc Web Admin."""
    try:
        data = await req.json()
        dev_id = data.get("device_id", "web_admin")
    except Exception:
        dev_id = "web_admin"
    ai_router.session_mgr.clear_session(dev_id)
    return JSONResponse({"status": "success", "message": f"Đã xóa ngữ cảnh trò chuyện của [{dev_id}]"})

# ==============================================================================
# NALA ADAPTIVE LEARNED MEMORY ENDPOINTS
# ==============================================================================

@app.get("/api/memory")
async def get_adaptive_memory():
    """Lấy toàn bộ thống kê và các mục trí nhớ Nala đã học được."""
    if not hasattr(ai_router, "memory_mgr"):
        return JSONResponse({"status": "error", "message": "Memory manager chưa được khởi tạo"}, status_code=500)
    return JSONResponse(ai_router.memory_mgr.get_summary())

@app.post("/api/memory/config")
async def save_adaptive_memory_config(req: Request):
    """Bật / Tắt chế độ tự học của Nala."""
    try:
        data = await req.json()
        enabled = bool(data.get("enabled", True))
        ai_router.memory_mgr.set_enabled(enabled)
        return JSONResponse({"status": "success", "enabled": enabled, "message": f"Đã {'bật' if enabled else 'tắt'} chế độ tự học!"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/memory/item")
async def add_adaptive_memory_item(req: Request):
    """Thêm hoặc sửa thủ công một mục trí nhớ (biệt danh hoặc thông tin gia đình)."""
    try:
        data = await req.json()
        item_type = data.get("type", "alias")
        if item_type == "alias":
            phrase = data.get("phrase", "").strip().lower()
            entity_id = data.get("entity_id", "").strip()
            room = data.get("room", "").strip()
            if not phrase or not entity_id:
                return JSONResponse({"status": "error", "message": "Vui lòng nhập đầy đủ cụm từ và Entity ID"}, status_code=400)
            aliases = ai_router.memory_mgr.data.setdefault("aliases", {})
            aliases[phrase] = {
                "entity_id": entity_id,
                "room": room,
                "hit_count": max(1, aliases.get(phrase, {}).get("hit_count", 1)),
                "last_used": time.time(),
                "confidence": 1.0
            }
            ai_router.memory_mgr._evict_if_needed()
            ai_router.memory_mgr.save_memory()
            return JSONResponse({"status": "success", "message": f"Đã lưu biệt danh '{phrase}' -> {entity_id}"})
        elif item_type == "fact":
            content = data.get("content", "").strip()
            category = data.get("category", "general").strip()
            if not content:
                return JSONResponse({"status": "error", "message": "Nội dung ghi nhớ không được để trống"}, status_code=400)
            added = ai_router.memory_mgr.add_fact(content, category)
            if added:
                return JSONResponse({"status": "success", "message": f"Đã thêm ghi nhớ: '{content}'"})
            else:
                return JSONResponse({"status": "error", "message": "Nội dung bị chặn hoặc trùng lặp"}, status_code=400)
        return JSONResponse({"status": "error", "message": "Loại mục nhớ không hợp lệ"}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.delete("/api/memory/item")
@app.post("/api/memory/delete")
async def delete_adaptive_memory_item(req: Request):
    """Xóa một mục trí nhớ (alias, habit hoặc fact)."""
    try:
        data = await req.json()
        item_type = data.get("type", "")
        item_id = data.get("id", "")
        if not item_type or not item_id:
            return JSONResponse({"status": "error", "message": "Thiếu type hoặc id của mục cần xóa"}, status_code=400)
        success = ai_router.memory_mgr.delete_item(item_type, item_id)
        if success:
            return JSONResponse({"status": "success", "message": f"Đã xóa thành công mục trí nhớ [{item_id}]"})
        return JSONResponse({"status": "error", "message": "Không tìm thấy mục cần xóa"}, status_code=404)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/memory/clean")
async def clean_adaptive_memory():
    """Dọn dẹp rác, ứng viên trôi hạn và các mục trí nhớ có độ tin cậy thấp."""
    try:
        cleaned_cnt = ai_router.memory_mgr.clean_garbage_and_decay()
        return JSONResponse({"status": "success", "message": f"Đã dọn dẹp {cleaned_cnt} mục trí nhớ rác và trôi hạn!"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/memory/reset")
async def reset_adaptive_memory():
    """Khôi phục trí nhớ Nala về trạng thái ban đầu."""
    try:
        ai_router.memory_mgr.reset_all_memory()
        return JSONResponse({"status": "success", "message": "Đã đặt lại toàn bộ trí nhớ Nala về mặc định thành công!"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/ai/chat/stream")
async def ai_chat_stream_endpoint(req: AIChatRequest):
    """
    Stream token-by-token real-time SSE for typewriter effect & Sentence-Chunked Pipelined Audio (Xiaozhi / Gemini style).
    SSE events:
    - event: token, data: {"chunk": "...", "accumulated": "..."}
    - event: sentence_audio, data: {"sentence_index": int, "text": "...", "audio_wav_base64": "..."}
    - event: audio, data: {"audio_wav_base64": "..."}
    - event: done, data: {"full_text": "...", "voice": "..."}
    """
    async def event_generator():
        accumulated = ""
        sentence_buffer = ""
        sentence_idx = 0
        voice = ai_router.config.get("tts_voice", "vi-VN-NamMinhNeural")

        def is_boundary(buf: str) -> bool:
            buf = buf.strip()
            words = buf.split()
            if len(words) < 2:
                return False
            if any(buf.endswith(p) for p in [".", "!", "?", "\n", "…"]):
                return True
            if any(buf.endswith(p) for p in [",", ":"]) and len(words) >= 5:
                return True
            if len(words) >= 11:
                return True
            return False

        async def render_sentence_wav(sent_text: str, idx: int):
            pcm = await audio_pipeline.text_to_pcm(sent_text, voice=voice)
            if pcm:
                import io, wave, base64
                wav_buf = io.BytesIO()
                with wave.open(wav_buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm)
                wav_b64 = base64.b64encode(wav_buf.getvalue()).decode('ascii')
                payload = json.dumps({"sentence_index": idx, "text": sent_text, "audio_wav_base64": wav_b64}, ensure_ascii=False)
                return f"event: sentence_audio\ndata: {payload}\n\n"
            return ""

        try:
            async for token in ai_router.stream_intent(req.message, model_preference=req.provider, device_id="web_admin"):
                accumulated += token
                sentence_buffer += token

                # 1. Bắn token chữ ra ngay cho hiệu ứng đánh máy (Typewriter)
                payload = json.dumps({"chunk": token, "accumulated": accumulated}, ensure_ascii=False)
                yield f"event: token\ndata: {payload}\n\n"

                # 2. Kiểm tra ngắt câu (Bí quyết Xiaozhi) -> Sinh audio câu này ngay!
                if is_boundary(sentence_buffer):
                    sent = sentence_buffer.strip()
                    sentence_buffer = ""
                    if sent:
                        evt = await render_sentence_wav(sent, sentence_idx)
                        sentence_idx += 1
                        if evt:
                            yield evt

            # 3. Render câu còn lại cuối cùng
            rem = sentence_buffer.strip()
            if rem:
                evt = await render_sentence_wav(rem, sentence_idx)
                if evt:
                    yield evt

            # 4. Tạo file audio hoàn chỉnh phục vụ nghe lại
            pcm = await audio_pipeline.text_to_pcm(accumulated, voice=voice)
            wav_b64 = ""
            if pcm:
                import io, wave, base64
                wav_buf = io.BytesIO()
                with wave.open(wav_buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(pcm)
                wav_b64 = base64.b64encode(wav_buf.getvalue()).decode('ascii')
                yield f"event: audio\ndata: {json.dumps({'audio_wav_base64': wav_b64})}\n\n"

            done_payload = json.dumps({"full_text": accumulated, "voice": voice}, ensure_ascii=False)
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as e:
            logger.error("Error in ai_chat_stream_endpoint: %s", e)
            err_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

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

    # Lưu bản theo đúng tên gốc upload (vd: firmware_v3.4.2.bin)
    orig_path = os.path.join(FIRMWARE_DIR, fname)
    with open(orig_path, "wb") as f:
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
async def download_firmware(filename: str, request: Request, code: Optional[str] = None):
    """Endpoint để ESP32-S3 tải stream file firmware binary qua HTTP GET, đồng thời phát sóng tiến độ theo thời gian thực tới Web Admin."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(FIRMWARE_DIR, safe_name)
    if not os.path.exists(file_path):
        latest_fallback = os.path.join(FIRMWARE_DIR, "firmware_latest.bin")
        if os.path.exists(latest_fallback):
            logger.info("File [%s] không tồn tại, tự động chuyển về [firmware_latest.bin]", safe_name)
            file_path = latest_fallback
            safe_name = "firmware_latest.bin"
        else:
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
    return FileResponse(file_path, filename=safe_name, media_type="application/octet-stream", headers=headers)

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
    firmware_url = f"http://{host}/api/ota/firmware/{filename}"

    if target_code.lower() == "all":
        for code, ws in list(active_sockets.items()):
            if not code.startswith("web_admin") and code != "default_panel":
                try:
                    ota_msg = {
                        "type": "ota_start",
                        "url": f"{firmware_url}?code={code}",
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
                device_firmware_url = f"{firmware_url}?code={target_code.upper()}"
                ota_msg = {
                    "type": "ota_start",
                    "url": device_firmware_url,
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

@app.delete("/api/history/session/{session_id}")
async def delete_history_session(session_id: str):
    count = history_mgr.delete_session(session_id)
    if count > 0:
        await broadcast_to_admins({"type": "history_session_deleted", "session_id": session_id})
        return JSONResponse({"status": "success", "message": f"Đã xóa {count} câu thoại trong phiên."})
    return JSONResponse({"status": "error", "message": "Phiên không tồn tại"}, status_code=404)

# -----------------------------------------------------------------------------
# REST ENDPOINTS FOR SPEAKER VOICEPRINT IDENTIFICATION (CAM++)
# -----------------------------------------------------------------------------
def convert_audio_to_pcm16k(audio_bytes: bytes) -> Optional[bytes]:
    """Chuyển đổi mọi định dạng âm thanh (WebM, OGG, MP3, WAV, AAC, raw PCM) sang 16kHz 16-bit Mono Linear PCM."""
    if not audio_bytes or len(audio_bytes) < 4:
        return None

    # 1. Fast path: Nếu là chuẩn file WAV 16kHz mono 16-bit
    if audio_bytes.startswith(b"RIFF") and b"WAVE" in audio_bytes[:12]:
        try:
            import io, wave
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                if wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == 16000:
                    return wf.readframes(wf.getnframes())
        except Exception:
            pass

    # 2. Sử dụng ffmpeg chuyển đổi tự động (hỗ trợ WebM, OGG, MP3, WAV đa kênh/tần số khác)
    import subprocess
    try:
        proc = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000", "pipe:1"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = proc.communicate(input=audio_bytes, timeout=8)
        if proc.returncode == 0 and out and len(out) > 0:
            return out
    except Exception as e:
        logger.warning("[FFMPEG] Convert warning: %s", e)

    # 3. Fallback: Nếu là raw PCM s16le không header
    if len(audio_bytes) % 2 == 0 and len(audio_bytes) >= 8000:
        return audio_bytes

    return None

class VoiceprintEnrollRequest(BaseModel):
    name: Optional[str] = None
    speaker_name: Optional[str] = None
    description: Optional[str] = None
    audio_base64: Optional[str] = None
    audio_list_base64: Optional[List[str]] = None
    record_id: Optional[str] = None
    filename: Optional[str] = None
    filenames: Optional[List[str]] = None

@app.get("/api/voiceprint/speakers")
async def get_voiceprint_speakers():
    """Lấy danh sách tất cả người dùng đã đăng ký vân giọng CAM++."""
    if not voiceprintManager or not getattr(voiceprintManager, "is_ready", False):
        return JSONResponse({"status": "unavailable", "speakers": [], "message": "Động cơ vân giọng chưa sẵn sàng"})
    speakers = voiceprintManager.list_speakers()
    return JSONResponse({"status": "success", "speakers": speakers, "count": len(speakers)})

@app.post("/api/voiceprint/enroll")
async def enroll_voiceprint_speaker(req: VoiceprintEnrollRequest):
    """Đăng ký vân giọng mới qua Base64 (WebM/WAV) hoặc từ file ghi âm trong lịch sử (đơn mẫu hoặc đa mẫu XiaoZhi style)."""
    if not voiceprintManager or not getattr(voiceprintManager, "is_ready", False):
        return JSONResponse({"status": "error", "message": "Động cơ vân giọng chưa được khởi tạo"}, status_code=503)

    target_name = (req.name or req.speaker_name or "").strip()
    if not target_name:
        return JSONResponse({"status": "error", "message": "Tên người dùng không được để trống"}, status_code=400)

    pcm_list: List[bytes] = []

    # 1. Đa mẫu từ Base64 (Micro trình duyệt)
    if req.audio_list_base64:
        import base64
        for b64 in req.audio_list_base64:
            try:
                raw = base64.b64decode(b64)
                pcm = convert_audio_to_pcm16k(raw)
                if pcm and len(pcm) >= 8000:
                    pcm_list.append(pcm)
            except Exception as e:
                logger.warning("Lỗi giải mã audio_list item: %s", e)

    # 2. Đơn mẫu từ Base64
    if req.audio_base64:
        import base64
        try:
            raw = base64.b64decode(req.audio_base64)
            pcm = convert_audio_to_pcm16k(raw)
            if pcm and len(pcm) >= 8000:
                pcm_list.append(pcm)
        except Exception as e:
            logger.warning("Lỗi giải mã audio_base64: %s", e)

    # 3. Đa mẫu từ filenames trong lịch sử ghi âm
    if req.filenames:
        for fn in req.filenames:
            audio_path = history_mgr.get_audio_path(fn)
            if audio_path and os.path.isfile(audio_path):
                try:
                    with open(audio_path, 'rb') as f:
                        raw = f.read()
                    pcm = convert_audio_to_pcm16k(raw)
                    if pcm and len(pcm) >= 8000:
                        pcm_list.append(pcm)
                except Exception as e:
                    logger.warning("Lỗi đọc file %s: %s", fn, e)

    # 4. Đơn mẫu từ filename/record_id
    if req.filename or req.record_id:
        target_fn = req.filename or f"{req.record_id}.wav"
        audio_path = history_mgr.get_audio_path(target_fn)
        if audio_path and os.path.isfile(audio_path):
            try:
                with open(audio_path, 'rb') as f:
                    raw = f.read()
                pcm = convert_audio_to_pcm16k(raw)
                if pcm and len(pcm) >= 8000:
                    pcm_list.append(pcm)
            except Exception as e:
                logger.warning("Lỗi đọc file %s: %s", target_fn, e)

    if not pcm_list:
        return JSONResponse({"status": "error", "message": "Không tìm thấy hoặc không thể chuyển đổi dữ liệu âm thanh hợp lệ (tối thiểu 0.5s)"}, status_code=400)

    ok, msg = voiceprintManager.enroll_multi(target_name, pcm_list, description=req.description or "")
    if ok:
        await broadcast_to_admins({"type": "voiceprint_updated", "speakers": voiceprintManager.list_speakers()})
        return JSONResponse({"status": "success", "message": msg, "name": target_name, "samples_count": len(pcm_list)})
    else:
        return JSONResponse({"status": "error", "message": msg}, status_code=400)

@app.delete("/api/voiceprint/speakers/{speaker_name}")
async def delete_voiceprint_speaker(speaker_name: str):
    """Xóa hồ sơ vân giọng của một người dùng."""
    if not voiceprintManager or not getattr(voiceprintManager, "is_ready", False):
        return JSONResponse({"status": "error", "message": "Động cơ vân giọng chưa sẵn sàng"}, status_code=503)
    ok = voiceprintManager.delete(speaker_name)
    if ok:
        await broadcast_to_admins({"type": "voiceprint_updated", "speakers": voiceprintManager.list_speakers()})
        return JSONResponse({"status": "success", "message": f"Đã xóa hồ sơ giọng của {speaker_name}"})
    return JSONResponse({"status": "error", "message": f"Không tìm thấy hồ sơ giọng {speaker_name}"}, status_code=404)

class VoiceprintIdentifyRequest(BaseModel):
    audio_base64: Optional[str] = None
    filename: Optional[str] = None
    threshold: Optional[float] = 0.58

@app.post("/api/voiceprint/identify")
async def identify_voiceprint_api(req: VoiceprintIdentifyRequest):
    """Thử nghiệm so khớp nhận diện vân giọng từ Audio Base64 (WebM/WAV) hoặc file ghi âm."""
    if not voiceprintManager or not getattr(voiceprintManager, "is_ready", False):
        return JSONResponse({"status": "error", "message": "Động cơ vân giọng chưa sẵn sàng"}, status_code=503)

    raw_bytes = None
    if req.audio_base64:
        try:
            import base64
            raw_bytes = base64.b64decode(req.audio_base64)
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Base64 không hợp lệ: {e}"}, status_code=400)
    elif req.filename:
        audio_path = history_mgr.get_audio_path(req.filename)
        if not audio_path or not os.path.isfile(audio_path):
            return JSONResponse({"status": "error", "message": f"Không tìm thấy file: {req.filename}"}, status_code=404)
        try:
            with open(audio_path, 'rb') as f:
                raw_bytes = f.read()
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Lỗi đọc file: {e}"}, status_code=500)

    if not raw_bytes:
        return JSONResponse({"status": "error", "message": "Thiếu dữ liệu audio"}, status_code=400)

    pcm_bytes = convert_audio_to_pcm16k(raw_bytes)
    if not pcm_bytes:
        return JSONResponse({"status": "error", "message": "Không thể chuyển đổi âm thanh sang 16kHz PCM"}, status_code=400)

    th = req.threshold or 0.58
    best_spk, best_sc, all_sc = voiceprintManager.identify(pcm_bytes, threshold=th)
    return JSONResponse({
        "status": "success",
        "matched_speaker": best_spk,
        "score": round(best_sc, 3),
        "threshold": th,
        "scores": all_sc
    })

@app.get("/api/living-context")
async def get_all_living_contexts():
    """Lấy danh sách ngữ cảnh sống thực tế (FSM) của các phòng."""
    if not livingContextEngine:
        return JSONResponse({"status": "unavailable", "contexts": {}})
    return JSONResponse({"status": "success", "contexts": livingContextEngine.get_all_contexts()})

@app.get("/api/automations")
async def get_automations():
    """Lấy danh sách các quy tắc tự động hóa phi tuyến tính."""
    if not automationEngine:
        return JSONResponse({"status": "unavailable", "rules": []})
    return JSONResponse({"status": "success", "rules": automationEngine.list_rules()})

@app.post("/api/automations")
async def add_automation(rule: Dict[str, Any]):
    """Thêm kịch bản tự động hóa mới."""
    if not automationEngine:
        return JSONResponse({"status": "error", "message": "Automation engine chưa sẵn sàng"}, status_code=503)
    created = automationEngine.add_rule(rule)
    return JSONResponse({"status": "success", "rule": created})

@app.put("/api/automations/{rule_id}")
async def update_automation(rule_id: str, rule: Dict[str, Any]):
    """Cập nhật kịch bản tự động hóa."""
    if not automationEngine:
        return JSONResponse({"status": "error", "message": "Automation engine chưa sẵn sàng"}, status_code=503)
    updated = automationEngine.update_rule(rule_id, rule)
    if updated:
        return JSONResponse({"status": "success", "rule": updated})
    return JSONResponse({"status": "error", "message": "Không tìm thấy kịch bản"}, status_code=404)

@app.delete("/api/automations/{rule_id}")
async def delete_automation(rule_id: str):
    """Xóa kịch bản tự động hóa."""
    if not automationEngine:
        return JSONResponse({"status": "error", "message": "Automation engine chưa sẵn sàng"}, status_code=503)
    ok = automationEngine.delete_rule(rule_id)
    if ok:
        return JSONResponse({"status": "success", "message": f"Đã xóa kịch bản {rule_id}"})
    return JSONResponse({"status": "error", "message": "Không tìm thấy kịch bản"}, status_code=404)

@app.post("/api/automations/{rule_id}/toggle")
async def toggle_automation(rule_id: str, payload: Optional[Dict[str, Any]] = None):
    """Bật/tắt kịch bản tự động hóa (nghịch đảo nếu không truyền payload)."""
    if not automationEngine:
        return JSONResponse({"status": "error", "message": "Automation engine chưa sẵn sàng"}, status_code=503)
    
    current_rule = next((r for r in automationEngine.rules if r.get("id") == rule_id), None)
    if not current_rule:
        return JSONResponse({"status": "error", "message": "Không tìm thấy kịch bản"}, status_code=404)
        
    if payload and "enabled" in payload:
        new_state = bool(payload["enabled"])
    else:
        new_state = not current_rule.get("enabled", False)
        
    ok = automationEngine.toggle_rule(rule_id, new_state)
    return JSONResponse({"status": "success", "rule_id": rule_id, "enabled": new_state})

# -----------------------------------------------------------------------------
# WEBSOCKET ENDPOINTS FOR ESP32 PANELS, NODES & WEB ADMIN
# -----------------------------------------------------------------------------
@app.websocket("/")
@app.websocket("/ws")
@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str = "default_panel"):
    await websocket.accept()
    client_ip = getattr(websocket.client, 'host', 'unknown') if hasattr(websocket, 'client') else 'unknown'
    logger.info("New WebSocket connection: %s (Client: %s)", device_id, client_ip)

    dev_code: Optional[str] = None
    if client_ip and client_ip != "unknown":
        for c, dev in devices_db.items():
            if dev.get("ip") == client_ip:
                dev_code = c
                active_sockets[dev_code] = websocket
                break

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
                        if code.startswith("TEST") or code.startswith("MOCK"):
                            logger.info("Ignoring persistent discovery for test client [%s]", code)
                            dev = {
                                "device_id": f"panel_{code.lower()}",
                                "mac": mac,
                                "pairing_code": code,
                                "ip": ip,
                                "model": model,
                                "firmware_version": fw_ver,
                                "room_name": "Phòng Thử Nghiệm",
                                "floor": "Tầng Trệt",
                                "is_paired": True,
                                "online": True,
                                "intercom_id": 99,
                                "buttons": [],
                                "entities": [],
                                "settings": {}
                            }
                        elif code not in devices_db:
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
                            dev = devices_db[code]
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

                        # Đồng bộ thời gian thực cho RTC nội bộ ESP32Time (1 lần duy nhất khi kết nối)
                        cur_epoch = int(time.time())
                        await websocket.send_json({
                            "type": "time_sync",
                            "epoch": cur_epoch
                        })

                        # Tự động sync cấu hình đã lưu xuống Panel kèm kênh đàm thoại & Từ khóa Wake Word
                        targets = intercom.get_targets(exclude_device_key=code)
                        rname = dev.get("room_name", f"Panel {code}")
                        active_wake_model = wake_mgr.config.get("selected_model", "hey_nala")
                        await websocket.send_json({
                            "type": "config_sync",
                            "epoch": cur_epoch,
                            "payload": {
                                "epoch": cur_epoch,
                                "room": f"{dev['room_name']} - {dev['floor']}",
                                "floor": dev['floor'],
                                "my_intercom_id": assigned_intercom_id,
                                "intercom_targets": targets,
                                "wake_word": get_wake_model_label(active_wake_model),
                                "wake_model": active_wake_model,
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

                # Yêu cầu lấy giờ từ Panel ESP32
                elif msg_type in ("get_time", "time_sync_request", "time_sync"):
                    await websocket.send_json({
                        "type": "time_sync",
                        "epoch": int(time.time())
                    })

                # Cập nhật Telemetry từ Radar mmWave HLK-LD2410 & Động cơ Ngữ cảnh sống FSM
                elif msg_type == "radar_event":
                    payload = data.get("payload", {})
                    if dev_code and dev_code in devices_db:
                        devices_db[dev_code]["radar"] = payload
                        r_name = devices_db[dev_code].get("room_name", dev_code)
                        living_state = "empty"
                        if livingContextEngine:
                            living_state = await livingContextEngine.update_radar_telemetry(dev_code, r_name, payload)
                            devices_db[dev_code]["living_context"] = living_state

                        # Broadcast trực tiếp cho Web Admin hiển thị trạng thái Real-time
                        await broadcast_to_admins({
                            "type": "radar_telemetry",
                            "device_id": dev_code,
                            "radar": payload,
                            "living_context": living_state
                        })

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
                    sender_key = dev_code or device_id
                    if action in ["abort", "stop", "barge_in"]:
                        await abort_ai_flow(sender_key, websocket)
                    elif action == "stop_ptt" and len(audio_record_buffers[device_id]) > 0:
                        pcm_audio = bytes(audio_record_buffers[device_id])
                        audio_record_buffers[device_id].clear()
                        task = asyncio.create_task(handle_ai_voice_flow(device_id, websocket, pcm_audio))
                        active_ai_tasks[device_id] = task

                # Lệnh cắt lời tức thì từ Web Client hoặc ESP32 (Xiaozhi Barge-in)
                elif msg_type in ["abort", "tts_stop"]:
                    sender_key = dev_code or device_id
                    await abort_ai_flow(sender_key, websocket)

                # Chạm nút Cúp Máy trên màn hình cảm ứng ESP32 hoặc Web Admin (Lớp 2: Touch Hangup)
                elif msg_type in ("intercom_hangup", "intercom_end_call"):
                    sender_k = dev_code or device_id
                    ended_sess = intercom.end_handsfree_call(sender_k, reason="touch_button")
                    if ended_sess:
                        hangup_payload = {"type": "intercom_hangup", "reason": "touch_button", "session_id": ended_sess.get("session_id")}
                        for k in (ended_sess.get("caller_key"), ended_sess.get("target_key")):
                            k_ws = active_sockets.get(k)
                            if k_ws:
                                try:
                                    await k_ws.send_json(hangup_payload)
                                except Exception:
                                    pass
                        await broadcast_to_admins({"type": "intercom_active_calls", "calls": intercom.get_active_calls_summary()})

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

                # Khi Panel báo timeout chế độ hội thoại liên tục (không phát hiện tiếng nói sau timeout)
                elif msg_type == "listen_timeout":
                    code = dev_code or device_id
                    wake_mgr.set_cooldown(code, duration_sec=4.0)
                    logger.info("Panel [%s] continuous listen timed out -> Saying farewell & closing session.", code)
                    # 1. Hủy buffer âm thanh rác và task AI đang chạy để chống vòng lặp
                    audio_record_buffers[code].clear()
                    await abort_ai_flow(code, websocket)
                    ai_router.session_mgr.clear_session(code)

                    # 2. Phát TTS câu chào tạm biệt qua loa chuẩn phong cách XiaoZhi
                    farewell_text = "Tạm biệt bạn nhé!"
                    try:
                        await websocket.send_json({"type": "tts", "state": "sentence_start", "text": farewell_text})
                        await websocket.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": farewell_text}})

                        tts_voice = ai_router.config.get("tts_voice", "google_fast")
                        fw_pcm = await audio_pipeline.text_to_pcm(farewell_text, voice=tts_voice)
                        if fw_pcm:
                            is_opus = (client_audio_formats.get(code) == "opus") and OPUS_AVAILABLE and not str(code).startswith("web_admin")
                            last_seq = await send_audio_chunks(websocket, fw_pcm, is_opus=is_opus, start_seq=0)
                            await send_audio_end(websocket, is_opus=is_opus, seq=last_seq)
                    except Exception as e:
                        logger.error("Error sending farewell TTS to %s: %s", code, e)
                    finally:
                        try:
                            await websocket.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
                        except Exception:
                            pass

            # 2. BINARY FRAME (Nén Opus 0xA55B HOẶC Raw PCM 520B 0xA55A)
            elif "bytes" in message:
                packet = message["bytes"]
                sender_key = dev_code or device_id

                # 2.1 KIỂM TRA GÓI TIN OPUS NÉN (0xA55B, >= 9 bytes)
                if len(packet) >= 9 and packet[0] == 0x5B and packet[1] == 0xA5:
                    client_audio_formats[sender_key] = "opus"
                    target_id = packet[3]
                    stream_flag = packet[6]
                    opus_len = int.from_bytes(packet[7:9], "little")
                    payload = packet[9:9+opus_len]

                    # Nếu là gói tin quét Wake Word (target_id == 0x05) qua nén Opus
                    if target_id == 0x05:
                        if opus_len > 0 and len(payload) >= opus_len and OPUS_AVAILABLE:
                            try:
                                if sender_key not in opus_decoders:
                                    opus_decoders[sender_key] = opuslib.Decoder(16000, 1)
                                pcm_chunk = opus_decoders[sender_key].decode(payload, 320)
                                asyncio.create_task(wake_mgr.feed_audio_chunk(sender_key, pcm_chunk))
                            except Exception as dec_err:
                                logger.warning(f"Lỗi giải mã Opus Wake chunk từ {sender_key}: {dec_err}")

                    # Gửi cho AI Voice Assistant (target_id == 0x00)
                    elif target_id == 0x00:
                        if sender_key not in audio_record_buffers:
                            audio_record_buffers[sender_key] = bytearray()

                        if stream_flag == 0x01: # START
                            if sender_key in active_ai_tasks:
                                await abort_ai_flow(sender_key, websocket)
                            audio_record_buffers[sender_key].clear()
                            if OPUS_AVAILABLE:
                                try:
                                    opus_decoders[sender_key] = opuslib.Decoder(16000, 1)
                                except Exception as e:
                                    logger.warning("Lỗi khởi tạo Opus Decoder cho %s: %s", sender_key, e)

                        # Giải mã frame nén Opus sang PCM 16kHz
                        if opus_len > 0 and len(payload) >= opus_len:
                            if OPUS_AVAILABLE and sender_key in opus_decoders:
                                try:
                                    pcm_chunk = opus_decoders[sender_key].decode(payload, 320)
                                    audio_record_buffers[sender_key].extend(pcm_chunk)
                                except Exception as dec_err:
                                    logger.warning("Lỗi giải mã Opus chunk từ %s: %s", sender_key, dec_err)

                        if stream_flag == 0x03: # END
                            pcm_audio = bytes(audio_record_buffers[sender_key])
                            audio_record_buffers[sender_key].clear()
                            task = asyncio.create_task(handle_ai_voice_flow(sender_key, websocket, pcm_audio, client_format="opus"))
                            active_ai_tasks[sender_key] = task
                    else:
                        # Gói Opus Intercom nội bộ
                        await intercom.route_binary_packet(sender_key, packet)

                # 2.2 GÓI TIN RAW PCM CŨ (0xA55A, 520 bytes)
                elif len(packet) == 520:
                    client_audio_formats[sender_key] = "pcm"
                    target_id = packet[3]
                    # Nếu là gói tin quét Wake Word (target_id == 0x05)
                    if target_id == 0x05:
                        pcm_chunk = packet[7:519]
                        stream_flag = packet[6]
                        if stream_flag == 0x01:
                            logger.info("[WAKE-STREAM] Bắt đầu nhận luồng Wake Word từ Panel [%s]", sender_key)
                        asyncio.create_task(wake_mgr.feed_audio_chunk(sender_key, pcm_chunk))
                    # Nếu là gói tin gửi cho AI (target_id == 0x00)
                    elif target_id == 0x00:
                        if sender_key not in audio_record_buffers:
                            audio_record_buffers[sender_key] = bytearray()
                        stream_flag = packet[6]
                        pcm_chunk = packet[7:519]
                        if stream_flag == 0x01: # START
                            # Ngắt lời tức thì nếu AI đang phát âm thanh câu trả lời trước đó (Barge-in)
                            if sender_key in active_ai_tasks:
                                await abort_ai_flow(sender_key, websocket)
                            audio_record_buffers[sender_key].clear()
                        audio_record_buffers[sender_key].extend(pcm_chunk)
                        if stream_flag == 0x03: # END
                            pcm_audio = bytes(audio_record_buffers[sender_key])
                            audio_record_buffers[sender_key].clear()
                            task = asyncio.create_task(handle_ai_voice_flow(sender_key, websocket, pcm_audio, client_format="pcm"))
                            active_ai_tasks[sender_key] = task
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
                                pcm_data=ic_pcm,
                                session_id=f"intercom_{int(time.time())}_{sender_key}",
                                ai_model="Intercom"
                            )
                            asyncio.create_task(broadcast_to_admins({"type": "history_new", "record": rec}))

                        await intercom.route_binary_packet(sender_key, packet)

                # 2.3 GÓI TIN RAW PCM TỪ WEB ADMIN / KIỂM THỬ MICRO PC
                else:
                    if sender_key.startswith("web_admin") or (len(packet) % 2 == 0 and len(packet) >= 128):
                        asyncio.create_task(wake_mgr.feed_audio_chunk(sender_key, packet))

    except WebSocketDisconnect:
        logger.info("Device disconnected: %s", dev_code or device_id)
    except Exception as e:
        logger.error("Error in websocket session for %s: %s", dev_code or device_id, e)
    finally:
        current_key = dev_code or device_id
        if device_id.startswith("web_admin"):
            intercom.unregister_admin(websocket)
            if active_sockets.get(device_id) == websocket:
                del active_sockets[device_id]
        if dev_code and active_sockets.get(dev_code) == websocket:
            intercom.unregister(dev_code, websocket)
            del active_sockets[dev_code]
            if dev_code in audio_record_buffers:
                del audio_record_buffers[dev_code]
            if dev_code in opus_decoders:
                del opus_decoders[dev_code]
            if dev_code in client_audio_formats:
                del client_audio_formats[dev_code]
            if dev_code in devices_db:
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

async def handle_ai_voice_flow(device_id: str, ws: WebSocket, pcm_audio: bytes, client_format: str = "auto"):
    """Luồng xử lý giọng nói hoàn chỉnh: STT -> AI Intent / HA Action -> Sentence Chunking TTS -> Gửi Binary Audio về ESP32."""
    curr_task = asyncio.current_task()
    active_ai_tasks[device_id] = curr_task
    wake_mgr.set_cooldown(device_id, duration_sec=5.0)
    try:
        # Phát âm thanh đã nhận trọn vẹn câu lệnh ("Poong!" - Xiaozhi Ack Style)
        await ws.send_json({"type": "ack_chime"})
        await ws.send_json({"type": "ai_state", "payload": {"state": "thinking", "text": "Đang suy nghĩ..."}})

        # 🎯 Nhận diện vân giọng (CAM++ 192-dim vector, ~20ms CPU) chạy song song với STT
        vp_task = None
        if voiceprintManager and getattr(voiceprintManager, "is_ready", False):
            vp_task = asyncio.create_task(asyncio.to_thread(voiceprintManager.identify, pcm_audio, 0.58))

        # 1. Speech-to-Text: Tự động ưu tiên Groq Whisper Turbo 0.15s (0% GPU NAS), fallback Faster-Whisper
        groq_cfg = ai_router.config.get("groq", {})
        groq_key = groq_cfg.get("api_key", "")
        stt_provider = ai_router.config.get("stt_provider", "auto")
        stt_model = ai_router.config.get("stt_groq_model", "whisper-large-v3-turbo")

        dev = devices_db.get(device_id, {})
        room_name = dev.get("room_name", "")
        tts_voice = ai_router.config.get("tts_voice", "google_fast")

        # STT Prompt Bias: Ghim từ vựng phòng hiện tại và danh mục smart home
        stt_prompt = f"Phòng {room_name}, {DEFAULT_SMART_HOME_WHISPER_PROMPT}" if room_name else DEFAULT_SMART_HOME_WHISPER_PROMPT

        text = await audio_pipeline.pcm_to_text(
            pcm_audio,
            groq_api_key=groq_key,
            stt_provider=stt_provider,
            groq_model=stt_model,
            prompt=stt_prompt
        )
        if not text or not text.strip():
            logger.info("[AI] Không có giọng nói hoặc phát hiện âm thanh rác từ [%s] -> Đưa về IDLE an toàn, dập tắt vòng lặp.", device_id)
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
            return

        # Thu hoạch kết quả nhận diện vân giọng
        identified_speaker = None
        vp_score = 0.0
        if vp_task:
            try:
                best_spk, best_sc, _ = await vp_task
                if best_spk:
                    spk_info = voiceprintManager.get_speaker_info(best_spk) if hasattr(voiceprintManager, "get_speaker_info") else {}
                    spk_desc = spk_info.get("description", "")
                    identified_speaker = f"{best_spk} ({spk_desc})" if spk_desc else best_spk
                    vp_score = best_sc
                    logger.info("[VOICEPRINT] 🎯 Xác thực thành công người nói: %s (score: %.3f)", identified_speaker, best_sc)
                    if livingContextEngine:
                        livingContextEngine.set_speaker_for_room(device_id, best_spk)
                    await broadcast_to_admins({
                        "type": "ai_speaker_identified",
                        "device_id": device_id,
                        "speaker": best_spk,
                        "score": round(best_sc, 3)
                    })
            except Exception as e:
                logger.warning("[VOICEPRINT] Lỗi khi nhận diện vân giọng: %s", e)

        # -------------------------------------------------------------
        # 🎙️ KIỂM TRA LỆNH ĐĂNG KÝ / HỌC VÂN GIỌNG (Voiceprint Enrollment)
        # -------------------------------------------------------------
        norm_text_lower = text.lower().strip()
        is_enroll_cmd = any(kw in norm_text_lower for kw in [
            "ghi nhớ giọng", "nhớ giọng của", "học giọng của", "học giọng", "lưu giọng", "đây là giọng của", "nhớ giọng tôi", "nhớ giọng anh"
        ])
        if is_enroll_cmd and voiceprintManager and getattr(voiceprintManager, "is_ready", False):
            import re
            m = re.search(r"(?:tên(?: là)?|tôi là|anh là|chị là|em là|giọng của)\s+([a-zA-ZÀ-ỹ0-9_]+)", text, re.IGNORECASE)
            spk_name = None
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in ["tôi", "bạn", "anh", "em", "chị", "ai", "gì", "nào", "mình", "người", "nhà"]:
                    spk_name = cand.capitalize()

            if spk_name:
                ok, msg = voiceprintManager.enroll(spk_name, pcm_audio)
                if ok:
                    reply_msg = f"Dạ, Nala đã ghi nhớ đặc trưng giọng nói của {spk_name} thành công rồi ạ! Từ bây giờ em sẽ nhận diện được {spk_name}."
                    await broadcast_to_admins({
                        "type": "voiceprint_updated",
                        "speakers": voiceprintManager.list_speakers()
                    })
                else:
                    reply_msg = f"Dạ, Nala chưa thể ghi nhớ giọng nói: {msg}"
            else:
                reply_msg = "Dạ, bạn muốn Nala ghi nhớ giọng với tên là gì ạ? Bạn hãy nói ví dụ: Ghi nhớ giọng của tôi, tôi tên là Tý."

            await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": reply_msg}})
            confirm_pcm = await audio_pipeline.text_to_pcm(reply_msg, voice=tts_voice)
            if confirm_pcm:
                is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                last_seq = await send_audio_chunks(ws, confirm_pcm, is_opus=is_opus, start_seq=0)
                await send_audio_end(ws, is_opus=is_opus, seq=last_seq)
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
            return

        # -------------------------------------------------------------
        # ⚙️ KIỂM TRA LỆNH CÀI ĐẶT TỰ ĐỘNG HÓA NGỮ CẢNH (Natural Language Automation)
        # -------------------------------------------------------------
        if automationEngine:
            auto_reply = automationEngine.parse_and_register_automation(
                text=text,
                context_room=room_name,
                speaker_name=identified_speaker
            )
            if auto_reply:
                await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": auto_reply}})
                confirm_pcm = await audio_pipeline.text_to_pcm(auto_reply, voice=tts_voice)
                if confirm_pcm:
                    is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                    last_seq = await send_audio_chunks(ws, confirm_pcm, is_opus=is_opus, start_seq=0)
                    await send_audio_end(ws, is_opus=is_opus, seq=last_seq)
                await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
                return

        # -------------------------------------------------------------
        # 📞 KIỂM TRA LỚP 1: CÚP MÁY BẰNG GIỌNG NÓI (Hands-Free Hangup)
        # -------------------------------------------------------------
        active_sess = intercom.get_active_session_for_device(device_id)
        norm_text = _normalize_vn(text)
        is_hangup_intent = any(k in norm_text for k in [
            "cup may", "tat cuoc goi", "ngat may", "dung goi",
            "thoi khong goi nua", "tat may", "cup di", "dung cuoc goi", "nala cup may"
        ])
        if active_sess and is_hangup_intent:
            ended_sess = intercom.end_handsfree_call(device_id, reason="voice_command")
            hangup_payload = {"type": "intercom_hangup", "reason": "voice_command", "session_id": active_sess.get("session_id")}
            for k in (active_sess.get("caller_key"), active_sess.get("target_key")):
                k_ws = active_sockets.get(k)
                if k_ws:
                    try:
                        await k_ws.send_json(hangup_payload)
                    except Exception:
                        pass
            confirm_pcm = await audio_pipeline.text_to_pcm("Đã cúp máy.", voice=tts_voice)
            if confirm_pcm:
                is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                last_seq = await send_audio_chunks(ws, confirm_pcm, is_opus=is_opus, start_seq=0)
                await send_audio_end(ws, is_opus=is_opus, seq=last_seq)
            await broadcast_to_admins({"type": "intercom_active_calls", "calls": intercom.get_active_calls_summary()})
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
            return

        # -------------------------------------------------------------
        # 📞 KIỂM TRA LỆNH GỌI LIÊN PHÒNG BẰNG GIỌNG NÓI ("Gọi cho phòng...")
        # -------------------------------------------------------------
        call_target = ai_router.detect_intercom_call_intent(text, intercom.get_targets(exclude_device_key=device_id))
        if call_target:
            t_key = call_target.get("code")
            t_name = call_target.get("name")
            t_online = call_target.get("online")
            target_ws = intercom.connections.get(t_key) or active_sockets.get(t_key)

            if t_online and target_ws:
                sess = intercom.start_handsfree_call(device_id, t_key)
                caller_ic_id = intercom.device_to_id.get(device_id, 1)
                target_ic_id = intercom.device_to_id.get(t_key, 2)
                await ws.send_json({
                    "type": "intercom_call_started",
                    "role": "caller",
                    "target_room": t_name,
                    "target_code": t_key,
                    "target_intercom_id": target_ic_id,
                    "caller_intercom_id": caller_ic_id,
                    "session_id": sess["session_id"]
                })
                await target_ws.send_json({
                    "type": "intercom_incoming_call",
                    "role": "callee",
                    "caller_room": room_name or f"Panel {device_id}",
                    "caller_code": device_id,
                    "caller_intercom_id": caller_ic_id,
                    "target_intercom_id": target_ic_id,
                    "auto_answer": True,
                    "session_id": sess["session_id"]
                })
                filler_pcm = await audio_pipeline.text_to_pcm(f"Dạ, đang kết nối với {t_name}...", voice=tts_voice)
                if filler_pcm:
                    is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                    last_seq = await send_audio_chunks(ws, filler_pcm, is_opus=is_opus, start_seq=0)
                    await send_audio_end(ws, is_opus=is_opus, seq=last_seq)

                await broadcast_to_admins({"type": "intercom_active_calls", "calls": intercom.get_active_calls_summary()})
                await ws.send_json({"type": "ai_state", "payload": {"state": "calling", "text": f"Đang đàm thoại với {t_name}..."}})
                return
            else:
                offline_reply = f"Phòng {t_name} hiện chưa kết nối hoặc đang ngoại tuyến ạ."
                off_pcm = await audio_pipeline.text_to_pcm(offline_reply, voice=tts_voice)
                if off_pcm:
                    is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                    last_seq = await send_audio_chunks(ws, off_pcm, is_opus=is_opus, start_seq=0)
                    await send_audio_end(ws, is_opus=is_opus, seq=last_seq)
                await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
                return

        # 2. Phân loại lệnh & Kiến trúc Pipelined Queue Phản xạ tức thì (Sub-200ms)

        lower_text = text.lower().strip()
        is_turn_on = any(w in lower_text for w in ["bật", "mở", "khởi động", "set", "chỉnh"])
        is_turn_off = any(w in lower_text for w in ["tắt", "đóng", "ngắt", "dừng"])
        is_master_off = any(w in lower_text for w in ["tắt hết", "tắt toàn bộ", "tắt cả nhà", "đi ngủ", "ra khỏi nhà"])
        is_device_keyword = any(w in lower_text for w in ["đèn", "quạt", "máy lạnh", "điều hòa", "ac", "công tắc", "ổ cắm", "rèm", "bình nóng lạnh"])

        # -------------------------------------------------------------
        # ⚡ CẤP ĐỘ 1: FAST-PATH SMART HOME (< 150ms TỨC THÌ)
        # -------------------------------------------------------------
        fast_handled = False
        fast_reply = ""

        # Ưu tiên 1: Khớp trực tiếp Biệt danh Trí Nhớ Nala (< 15ms)
        if hasattr(ai_router, "memory_mgr") and ai_router.memory_mgr.is_enabled():
            mem_match = ai_router.memory_mgr.match_fast_path(text, context_room=room_name)
            if mem_match and ai_router.ha_bridge:
                target_eid = mem_match["entity_id"]
                target_act = mem_match["action"]
                target_dom = target_eid.split(".")[0]
                action_viet = "bật" if target_act == "turn_on" else "tắt"
                ha_ok = await ai_router.ha_bridge.call_service(target_dom, target_act, {"entity_id": target_eid})
                if ha_ok:
                    fast_reply = f"Đã {action_viet} {mem_match.get('phrase', target_eid)}."
                    fast_handled = True
                    ai_router.memory_mgr.learn_device_interaction(text, target_eid, context_room=room_name, domain=target_dom, action=target_act)

        if not fast_handled:
            # Ưu tiên 1.5: Suy luận Ý định gián tiếp (Nóng quá, Lạnh quá, Tối quá, Đi ngủ, Ra ngoài)
            indirect_res = await ai_router.handle_indirect_intent(text, context_room=room_name)
            if indirect_res:
                fast_reply = indirect_res
                fast_handled = True

        if not fast_handled:
            if is_master_off and ai_router.ha_bridge:
                res = await ai_router.ha_bridge.master_turn_off_all()
                cnt = res.get("turned_off_count", 0)
                fast_reply = f"Đã tắt toàn bộ {cnt} thiết bị trong nhà cho bạn."
                fast_handled = True
            elif (is_turn_on or is_turn_off) and is_device_keyword and ai_router.ha_bridge:
                local_res = await ai_router._try_local_rule_fallback(text, context_room=room_name)
                if local_res:
                    fast_reply = local_res
                    fast_handled = True

        if fast_handled and fast_reply:
            # 1. Phát ngay Done Chime ("Ting!" 80ms) tới ESP32 trong < 50ms!
            try:
                await ws.send_json({"type": "done_chime"})
            except Exception:
                pass

            # 2. Hiển thị UI tức thì trên màn hình LVGL
            await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": fast_reply}})

            # 3. Phát âm thanh xác nhận ngắn từ RAM Cache (< 10ms)
            confirm_pcm = await audio_pipeline.text_to_pcm(fast_reply, voice=tts_voice)
            if confirm_pcm:
                is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
                last_seq = await send_audio_chunks(ws, confirm_pcm, is_opus=is_opus, start_seq=0)
                await send_audio_end(ws, is_opus=is_opus, seq=last_seq)

            sess_id = ai_router.session_mgr.get_session_id(device_id)
            turn_idx = 1
            if fast_reply:
                turn_idx = ai_router.session_mgr.add_turn(device_id, text, fast_reply) or 1

            rec = history_mgr.add_record(
                device_code=device_id,
                room_name=dev.get("room_name", f"Panel {device_id}"),
                session_type="voice_ai",
                text=text,
                response=fast_reply,
                pcm_data=pcm_audio,
                session_id=sess_id,
                turn_index=turn_idx,
                ai_model="⚡ Fast Rule (0ms)",
                speaker=identified_speaker
            )
            asyncio.create_task(broadcast_to_admins({"type": "history_new", "record": rec}))

            continuous_enabled = ai_router.config.get("continuous_conversation", True)
            is_farewell = ai_router.session_mgr.is_farewell(text)

            if continuous_enabled and not is_farewell:
                timeout_ms = int(ai_router.config.get("continuous_timeout_ms", 8000))
                logger.info("[CONTINUOUS] Bắt đầu phiên lắng nghe tiếp nối sau fast-rule cho [%s] (timeout: %dms)...", device_id, timeout_ms)
                await ws.send_json({
                    "type": "start_listen",
                    "payload": {
                        "timeout_ms": timeout_ms,
                        "mode": "continuous",
                        "text": "Đang nghe tiếp..."
                    }
                })
                await ws.send_json({
                    "type": "ai_state",
                    "payload": {
                        "state": "listening",
                        "text": "Đang nghe tiếp...",
                        "continuous": True
                    }
                })
            else:
                await ws.send_json({"type": "ai_state", "payload": {"state": "idle"}})
            return

        # -------------------------------------------------------------
        # 🧠 CẤP ĐỘ 2: HỎI ĐÁP / HỘI THOẠI AI: PIPELINED GAPLESS STREAMING (0ms KHOẢNG LẶNG)
        # -------------------------------------------------------------
        # audio_queue: Chứa tuple (sent_idx: int, sent_text: str, pcm_bytes: Optional[bytes], is_final: bool)
        audio_queue = asyncio.Queue()
        sentence_queue = asyncio.Queue()  # Chứa str (nội dung câu) hoặc None (kết thúc)
        accumulated_text = ""

        # Nạp ngay Instant Audio Filler ("Dạ,") vào đầu Queue nếu có trong Cache
        # Giúp loa ESP32 bật tiếng ngay sau 50ms khi người dùng vừa dứt lời!
        filler_pcm = await audio_pipeline.text_to_pcm("Dạ,", voice=tts_voice)
        if filler_pcm:
            await audio_queue.put((0, "Dạ,", filler_pcm, False))

        def is_boundary(buf: str) -> bool:
            buf = buf.strip()
            words = buf.split()
            if len(words) < 5:
                return False
            # Chỉ ngắt ở dấu kết thúc câu thật sự: . ! ? \n …
            if any(buf.endswith(p) for p in [".", "!", "?", "\n", "…"]):
                return True
            # Nếu câu quá dài (> 20 từ) và có dấu phẩy hoặc chấm phẩy mới ngắt nhịp thở
            if any(buf.endswith(p) for p in [",", ";"]) and len(words) >= 20:
                return True
            return False

        def trim_pcm_silence(pcm_data: bytes, threshold: int = 250) -> bytes:
            """Cắt bỏ khoảng lặng (silence padding) ở đầu và cuối để nối mượt mà 0ms khoảng trống."""
            if not pcm_data or len(pcm_data) < 4:
                return pcm_data
            try:
                import numpy as np
                samples = np.frombuffer(pcm_data, dtype=np.int16)
                non_silent = np.where(np.abs(samples) > threshold)[0]
                if len(non_silent) == 0:
                    return pcm_data
                start_idx = max(0, non_silent[0] - 160) # Giữ 10ms đệm êm
                end_idx = min(len(samples), non_silent[-1] + 160)
                return samples[start_idx:end_idx].tobytes()
            except Exception:
                return pcm_data

        async def llm_producer():
            nonlocal accumulated_text
            sentence_buffer = ""
            last_ws_send_time = 0.0
            try:
                loop = asyncio.get_event_loop()
                async for token in ai_router.stream_intent(text, context_room=room_name, device_id=device_id, speaker_name=identified_speaker):
                    accumulated_text += token
                    sentence_buffer += token

                    now = loop.time()
                    # Điều tốc mượt cho màn hình ESP32: nhịp thở tự nhiên theo từ hoặc tối thiểu 50ms
                    if (now - last_ws_send_time >= 0.06) or token.endswith((" ", ".", ",", "!", "?", "\n")):
                        last_ws_send_time = now
                        await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": accumulated_text}})

                    if is_boundary(sentence_buffer):
                        sent = sentence_buffer.strip()
                        sentence_buffer = ""
                        if sent:
                            await sentence_queue.put(sent)

                # Đảm bảo hiển thị trọn vẹn văn bản cuối cùng lên màn hình ESP32
                await ws.send_json({"type": "ai_state", "payload": {"state": "speaking", "text": accumulated_text}})

                rem = sentence_buffer.strip()
                if rem:
                    await sentence_queue.put(rem)
            except asyncio.CancelledError:
                raise
            except Exception as ex:
                logger.error("Error in LLM stream producer: %s", ex)
            finally:
                await sentence_queue.put(None)  # Báo hiệu hết token từ LLM

        async def tts_worker():
            """Tổng hợp câu tiếp theo song song trong RAM trong lúc câu trước đang phát ra loa."""
            sent_idx = 1 if filler_pcm else 0
            while True:
                sent = await sentence_queue.get()
                if sent is None:
                    await audio_queue.put((0, "", None, True))  # Hết toàn bộ bài nói
                    break
                try:
                    chunk_pcm = await audio_pipeline.text_to_pcm(sent, voice=tts_voice)
                    if chunk_pcm:
                        trimmed = trim_pcm_silence(chunk_pcm)
                        await audio_queue.put((sent_idx, sent, trimmed, False))
                        sent_idx += 1
                except asyncio.CancelledError:
                    raise
                except Exception as ex:
                    logger.warning("TTS error for chunk '%s': %s", sent, ex)

        async def audio_streamer():
            """Đẩy liên tục audio xuống ESP32, câu 2 nối tiếp câu 1 với 0ms khoảng lặng."""
            seq = 0
            is_opus = (client_format == "opus" or (client_format == "auto" and client_audio_formats.get(device_id) == "opus")) and OPUS_AVAILABLE and not device_id.startswith("web_admin")
            opus_enc = None
            if is_opus:
                try:
                    opus_enc = opuslib.Encoder(16000, 1, 'voip')
                except Exception as e:
                    logger.warning("Không thể tạo Opus Encoder cho stream: %s", e)
                    is_opus = False

            while True:
                sent_idx, sent_text, item, is_final = await audio_queue.get()
                if is_final:
                    break
                if not item:
                    continue

                # Chuẩn hóa sự kiện sentence_start đồng bộ chữ và tiếng (Xiaozhi Style)
                if sent_text:
                    try:
                        # Chuẩn Xiaozhi: {"type": "tts", "state": "sentence_start", "text": "..."}
                        await ws.send_json({
                            "type": "tts",
                            "state": "sentence_start",
                            "text": sent_text,
                            "index": sent_idx
                        })
                        # Gửi thêm dạng payload để tương thích ngược hoàn hảo
                        await ws.send_json({
                            "type": "sentence_start",
                            "payload": {
                                "index": sent_idx,
                                "text": sent_text
                            }
                        })
                    except Exception:
                        pass

                seq = await send_audio_chunks(ws, item, is_opus=is_opus, start_seq=seq, encoder=opus_enc)

            # Gửi gói kết thúc STREAM_FLAG_END (0x03) duy nhất một lần khi nói xong toàn bộ
            await send_audio_end(ws, is_opus=is_opus, seq=seq)

        # Chạy song song cả 3 worker qua asyncio.gather
        await asyncio.gather(
            llm_producer(),
            tts_worker(),
            audio_streamer()
        )

        # Ghi nhận lượt nói vào bộ nhớ ngữ cảnh và lấy session ID
        sess_id = ai_router.session_mgr.get_session_id(device_id)
        turn_idx = 1
        if accumulated_text and not accumulated_text.startswith("Xin lỗi") and not accumulated_text.startswith("Tôi không nghe"):
            turn_idx = ai_router.session_mgr.add_turn(device_id, text, accumulated_text) or 1

        # Lưu vào Lịch sử Giọng nói & Ghi âm Audio
        target_ai_model = ai_router.config.get("llm_model") or ai_router.config.get("gemini", {}).get("model", "gemini-2.0-flash")
        rec = history_mgr.add_record(
            device_code=device_id,
            room_name=dev.get("room_name", f"Panel {device_id}"),
            session_type="voice_ai",
            text=text,
            response=accumulated_text,
            pcm_data=pcm_audio,
            session_id=sess_id,
            turn_index=turn_idx,
            ai_model=target_ai_model,
            speaker=identified_speaker
        )
        asyncio.create_task(broadcast_to_admins({"type": "history_new", "record": rec}))

        # Kiểm tra cơ chế Trò Chuyện Liên Tục (Xiaozhi Style)
        continuous_enabled = ai_router.config.get("continuous_conversation", True)
        is_farewell = ai_router.session_mgr.is_farewell(text)

        # Nếu AI không sinh được câu trả lời (do lỗi API/rỗng), kết thúc phiên ngay để chống kẹt vòng lặp suy nghĩ
        if not accumulated_text:
            logger.warning("[AI] LLM không sinh được câu trả lời cho [%s], đưa về IDLE chống kẹt vòng lặp.", device_id)
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": "Em chưa nghe rõ, bạn nói lại nhé."}})
            return

        if continuous_enabled and not is_farewell:
            timeout_ms = int(ai_router.config.get("continuous_timeout_ms", 8000))
            logger.info("[CONTINUOUS] Bắt đầu phiên lắng nghe tiếp nối cho [%s] (timeout: %dms)...", device_id, timeout_ms)
            # 1. Gửi lệnh start_listen kích hoạt mic ESP32 với đếm ngược timeout
            await ws.send_json({
                "type": "start_listen",
                "payload": {
                    "timeout_ms": timeout_ms,
                    "mode": "continuous",
                    "text": "Đang nghe tiếp..."
                }
            })
            # 2. Cập nhật trạng thái listening cho màn hình
            await ws.send_json({
                "type": "ai_state",
                "payload": {
                    "state": "listening",
                    "text": "Đang nghe tiếp...",
                    "continuous": True
                }
            })
        else:
            logger.info("[SESSION] Kết thúc phiên trò chuyện cho [%s], đưa về IDLE.", device_id)
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle"}})

    except asyncio.CancelledError:
        logger.info("[BARGE-IN] AI flow của [%s] đã bị hủy tức thì bởi người dùng (Cắt lời thành công).", device_id)
        try:
            await ws.send_json({"type": "tts_stop"})
            await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": ""}})
        except Exception:
            pass
        raise
    except Exception as e:
        import traceback
        logger.error("Error in AI voice flow for %s: %s\n%s", device_id, e, traceback.format_exc())
        await ws.send_json({"type": "ai_state", "payload": {"state": "idle", "text": "Lỗi xử lý âm thanh."}})
    finally:
        if active_ai_tasks.get(device_id) is curr_task:
            active_ai_tasks.pop(device_id, None)

if __name__ == "__main__":
    uvicorn.run("app.main_ws_server:app", host="0.0.0.0", port=PORT, reload=False)
